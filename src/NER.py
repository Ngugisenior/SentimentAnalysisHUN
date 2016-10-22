#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, getopt, csv
from polyglot.text import Text
from itertools import chain
from Morphological_Disambiguation import StemmedForm
from Morphological_Disambiguation import MorphologicalDisambiguation
from Postprocess import StopWordFilter
from Postprocess import NumberFilter

# This function creates 3 dictionaries for location, person and organization. Important, every result set is in UNICODE encoding! 
def NER_Dictionary(CorpusFilePath):
	corpusfile = open(CorpusFilePath, 'rb')
	csvreader = csv.reader(corpusfile, delimiter='\t')

	locationList = []
	personList = []
	organizationList = []

	for line in csvreader:
		try:
			blob = str(line[4]).decode('latin2')
			text = Text(blob)
			for sent in text.sentences:
				for entity in sent.entities:
					tag = entity.tag
					for element in entity:
						if element.encode('latin2') not in chain(personList, locationList, organizationList):
					    		if 'PER' in tag:
								personList.append(element.encode('latin2'))
							elif 'LOC' in tag:
								locationList.append(element.encode('latin2'))
							elif 'ORG' in tag:
								organizationList.append(element.encode('latin2'))
		except:
			pass
	
	# Filter out some mistaken nouns
	person = []
	for word in personList:
    		if word[0].isupper():
        		person.append(word)

	# Sort them to make it more understandable for human beings
	locationList = sorted(locationList)
	personList = sorted(person)
	organizationList = sorted(organizationList)	

	return (locationList, personList, organizationList)

def NERfilter(sentencesArray, filterList):
	filteredArray = []
	for sentence in sentencesArray:
		filteredSentence = []
		for word in sentence:
			#if [s for s in filterList if word not in s]:
			if word not in filterList:			
				filteredSentence.append(word)
			
		filteredArray.append(filteredSentence)

	return filteredArray
	

def main():
	PreprocessedCorpusPath='/home/osboxes/NLPtools/SentAnalysisHUN-master/OpinHuBank_20130106_new.csv'
	(locationList, personList, organizationList) = NER_Dictionary(PreprocessedCorpusPath)

	#print personList
	
	# TESTING NER_FILTERING
	MorphResultsFilePath='/home/osboxes/NLPtools/SentAnalysisHUN-master/morph_ki.txt'
	PreprocessedCorpusPath='/home/osboxes/NLPtools/SentAnalysisHUN-master/OpinHuBank_20130106_new.csv'
	TFIDFthreshold=0.4	
	stopwordsFilePath='/home/osboxes/Desktop/SentimentAnalysisHUN/resources/stopwords.txt'
	IntervalNumber=5
	OnOffFlag=1
	
	posfilePath='/home/osboxes/NLPtools/SentAnalysisHUN-master/hunpos_ki.txt'
	morphfilePath='/home/osboxes/NLPtools/SentAnalysisHUN-master/hunmorph_ki.txt'
	
	# Morphological disambiguation
	(wordsArray, disArray) = MorphologicalDisambiguation(posfilePath, morphfilePath)
	Array = StemmedForm(disArray, 0)
	
	# Stopword filtering
	filtArray = StopWordFilter(Array, stopwordsFilePath)
	
	NERArray = NERfilter(filtArray, personList)
	NERArray = NERfilter(NERArray, locationList)
	NERArray = NERfilter(NERArray, organizationList)
	print NERArray
	#print filtArray[(len(filtArray)-4):len(filtArray)]

	

if __name__ == "__main__":
   	main()
