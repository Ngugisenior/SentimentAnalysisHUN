import matplotlib.pyplot as plt
import csv
import pandas
import sklearn
import cPickle
import numpy as np
from scipy.stats import pearsonr
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC, LinearSVC
from sklearn.metrics import classification_report, f1_score, accuracy_score, confusion_matrix
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split, learning_curve

from Morphological_Disambiguation import MorphologicalDisambiguation
from Morphological_Disambiguation import StemmedForm
from Postprocess import StopWordFilter
from Postprocess import NumberFilter
from FeatureExtraction import SentimentDictionary_Read
from FeatureExtraction import n_gram
from FeatureExtraction import replace_if_occurances
from FeatureExtraction import get_words_from_array

# Create a List containing all inputs in unicode encoding for CountVectorizer specific input purpose
def CountVectorizerTransform_input(inputList):
	outputList = []	
	for sentence in inputList:
		outputList.append(str(' '.join(sentence)))	#unicode(str(' '.join(sentence)),'latin2'))
	return outputList


# Get ratings from SentimentCorpus with an option to have category reduction ability
def GetRatingsFromCorpus(FilePath, RatingsReduction):
	ratings = []
	corpusfile = open(FilePath,'rb')
	csvreader = csv.reader(corpusfile, delimiter='\t')
	
	for row in csvreader:
		reviewScore = 0
		for i in range(6,11):
			if row[i] == '-1':
				reviewScore -= 1
			elif row[i] == '1':
				reviewScore += 1

		# RatingsReduction with option except 1: 1 (pos) and 0 (neg) or not
		if RatingsReduction == 0:			
			ratings.append(reviewScore)
		else:
			if reviewScore > 0:
				ratings.append('positive')
			elif reviewScore < 0:
				ratings.append('negative')
			else:
				ratings.append('neutral')

	corpusfile.close()
	
	return ratings

# Save predictor model
def savePredictor(predictorName, predictorFilePath):
	with open(predictorFilePath, 'wb') as file_out:
    		cPickle.dump(predictorName, file_out)

	file_out.close()


# This feature is to determine sentiment dictionary occurances by each tuple
class SentDictOccurancesFeature(BaseEstimator, TransformerMixin):
	# gets list for both posDict and negDict
	def __init__(self, posDict='', negDict=''):
		self.posDict = posDict
		self.negDict = negDict	
    	
	def fit(self, raw_documents, y=None):
       		return self
    	
	def fit_transform(self, raw_documents, y=None):
		return self.transform(raw_documents)

	def transform(self, raw_documents, y=None):
		PosNegOccurances = np.recarray(shape=(len(raw_documents),1), dtype=[('positive', int), ('negative', int)])		
		for i, sentence in enumerate(raw_documents):		
			PosOccurances = 0
			NegOccurances = 0	
			words = sentence.split()
			for word in words:
				if word in self.posDict:
					PosOccurances += 1
				elif word in self.negDict:
					NegOccurances += 1	

			PosNegOccurances['positive'][i]= PosOccurances
			PosNegOccurances['negative'][i]= NegOccurances	
		
		return PosNegOccurances

# Itemselector for SentDictOccurancesFeature
class ItemSelector(BaseEstimator, TransformerMixin):
    def __init__(self, key):
        self.key = key

    def fit(self, x, y=None):
        return self

    def transform(self, data_dict):
        return data_dict[self.key]


def main():
	
	# Some info to apply morphological disambiguation and create stemmed form 
	PreprocessedCorpusPath='/home/osboxes/NLPtools/SentAnalysisHUN-master/OpinHuBank_20130106_new_with_posneg.csv'
	posfilePath='/home/osboxes/NLPtools/SentAnalysisHUN-master/hunpos_ki_with_posneg.txt'
	morphfilePath='/home/osboxes/NLPtools/SentAnalysisHUN-master/hunmorph_ki_with_posneg.txt'
	stopwordsFilePath='/home/osboxes/Desktop/SentimentAnalysisHUN/resources/stopwords.txt'
	
	# Morphological disambiguation (wordsArray contains original words - for easier n-gram filtering, disArray for perfect output)
	(wordsArray, disArray) = MorphologicalDisambiguation(posfilePath, morphfilePath)
	stemmedArray = StemmedForm(disArray, 0)
	
	# Substitute rare words with specific label '_rare_'
	substArray = replace_if_occurances(stemmedArray, get_words_from_array(stemmedArray), 3, '_rare_')

	# 5-gram usage example
	n_Array = n_gram(wordsArray, substArray, PreprocessedCorpusPath, 5, 0)
	
	# Stopword filtering 
	stopwordfiltArray = StopWordFilter(n_Array, stopwordsFilePath)

	# Number filtering
	filtArray = NumberFilter(stopwordfiltArray)

	###################################################
	### Machine learning part with sklearn.pipeline ###
	###################################################

	# labels -  you can filter it to positive / negative as well
	labels = GetRatingsFromCorpus(PreprocessedCorpusPath, 1)

	# convert filtArray to new CountVect input format	
	new_filtArray = CountVectorizerTransform_input(filtArray)
	
	# create test and training set with divide corpus into two parts
	trainingSet, testSet, trainingLabel, testLabel = train_test_split(new_filtArray, labels, test_size=0.2)
	
	# load sentiment lexicons from external files
	posLexicon = SentimentDictionary_Read('/home/osboxes/Desktop/SentimentAnalysisHUN/resources/SentimentLexicons/PrecoNeg.txt')
	negLexicon = SentimentDictionary_Read('/home/osboxes/Desktop/SentimentAnalysisHUN/resources/SentimentLexicons/PrecoPos.txt')
	
	# create sklearn.pipeline for automated machine learning
	pipeline = Pipeline([
		# Transform inputlist to pipeline format
		#('transform', TransformationForPipeline()),
	    # Feature extraction part
	    ('features', FeatureUnion(
			transformer_list=[

			    # TF-IDF to have a more accurate overview on words, which have a huge influance on sentiment analysis
			    ('tfidf', Pipeline([
					('basic_cv', CountVectorizer(encoding='latin2')),
					('tfidf', TfidfTransformer()),
			    ])),

			    # Positive and negative sentiment dictionary occurances as a feature
			    ('sentdic_positive', Pipeline([
					('sentDicOcc', SentDictOccurancesFeature(posDict=posLexicon, negDict=negLexicon)),
					('posOcc', ItemSelector(key='positive'))
			    ])),
			    ('sentdic_negative', Pipeline([
					('sentDicOcc', SentDictOccurancesFeature(posDict=posLexicon, negDict=negLexicon)),
					('negOcc', ItemSelector(key='negative'))
			    ])),

			],

			# weight components in FeatureUnion
			transformer_weights={
			    'tfidf': 1.0,
			    'sentdic_positive': 0.5,
			    'sentdic_negative': 0.5,
			},
	    	)),
	   # Naive Bayes classifier
	   ('classifier', MultinomialNB()),
	])

	# use gridsearchCV for automated machine learning with multiple options - "parameters"
	params = {
	    'classifier__alpha': [1.0], 	#[0.5, 0.75, 1.0, 1.25, 1.5],
	    'classifier__class_prior': [None],
	    'classifier__fit_prior': [True],
	}

	grid = GridSearchCV(
	    pipeline,  				# pipeline from above
	    params,  				# parameters to tune via cross validation
	    refit=True,  			# fit using all available data at the end, on the best found param combination
	    n_jobs=-1,  			# number of cores to use for parallelization; -1 for "all cores"
	    scoring='accuracy',  		# what score are we optimizing?
	    cv=StratifiedKFold(n_splits=10).get_n_splits(trainingSet, trainingLabel),  # what type of cross validation to use
	)
	
	# predictive model training
	clf = grid.fit(trainingSet, trainingLabel)
	
	# predictive model results with different options determined at parameters
	means = clf.cv_results_['mean_test_score']
    	stds = clf.cv_results_['std_test_score']
	print means
	print stds

	# evaluation part with precision, recall, f-score
	predictions = clf.predict(testSet)			# predictions for test set
	print "ContegencyTableValues"
	print confusion_matrix(testLabel, predictions)		# TP, TF, ... values
	print "Evaluation scores"
	print classification_report(testLabel, predictions)	# precision, recall, f-score
	try:
		print "Pearson correlation"
		print pearsonr(testLabel, predictions)
		print np.corrcoef(testLabel, predictions)
	except:
		pass
	
	print "\nTest:"	
	testSent1 = ["ez egy nagyon rossz nap"]
	print testSent1
	print clf.predict(testSent1)
	testSent2 = ["hihetetlen boldog vagyok nagyon szuper"]
	print testSent2
	print clf.predict(testSent2)
	testSent3 = ["az alma angolul apple"]
	print testSent3
	print clf.predict(testSent3)	

if __name__ == '__main__':
	main()
