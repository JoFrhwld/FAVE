#!/usr/bin/env python

## Python script for merging two versions of the CMU dictionary
## written by Ingrid Rosenfelder
## last modified June 23, 2010

"""Usage:  python merge_dicts.py dict1 dict2 merged_dict"""

import sys
import re

def read_dict(f):
    """reads the CMU dictionary and returns it as dictionary object,
    allowing multiple pronunciations for the same word"""
    ## INPUT:  string f = name/path of dictionary file
    ## OUTPUT:  dict cmudict = dictionary of word - (list of) transcription(s) pairs
    ## (where each transcription consists of a list of phones)
    
    dictfile = open(f, 'rU')
    lines = dictfile.readlines()
    cmudict = {}
    pat = re.compile('  *')                ## two spaces separating CMU dict entries
    for line in lines:
        line = line.rstrip()
        line = re.sub(pat, ' ', line)      ## reduce all spaces to one
        word = line.split(' ')[0]          ## orthographic transcription
        phones = line.split(' ')[1:]       ## phonemic transcription
        if word not in cmudict:
            cmudict[word] = [phones]       ## phonemic transcriptions represented as list of lists of phones
        else:
            ## check that transcription does not exist already!
            if not phones in cmudict[word]:
                cmudict[word].append(phones)   ## add alternative pronunciation to list of pronunciations
    dictfile.close()
    ## check that cmudict has entries
    if len(cmudict) == 0:
        sys.exit("ERROR!  CMU dictionary is empty.")
    print "Read CMU dictionary from file %s." % f
    return cmudict


def write_dict(f, d):
    """writes the new version of the CMU dictionary to file"""
    out = open(f, 'w')
    ## sort dictionary before writing to file
    s = d.keys()
    s.sort()
    for w in s:
        ## make a separate entry for each pronunciation in case of alternative entries
        for t in d[w]:
            out.write(w + '  ')     ## two spaces separating CMU dict entries from phonetic transcriptions
            for p in t:
                out.write(p + ' ')  ## list of phones, separated by spaces
            out.write('\n')         ## end of entry line
    out.close()
    print "Written updated pronunciation dictionary to file."


def merge_dicts(d1, d2):
    """merges two versions of the CMU pronouncing dictionary"""
    ## for each word, each transcription in d2, check if present in d1
    for word in d2:
        ## if no entry in d1, add entire entry 
        if word not in d1:
            d1[word] = d2[word]
        ## if entry in d1, check whether additional transcription variants need to be added
        else:
            for t in d2[word]:
                if t not in d1[word]:
                    d1[word].append(t)
    return d1
    

###############################################################################################################

if __name__ == '__main__':

    try:
        dict1 = sys.argv[1]
        dict2 = sys.argv[2]
        merged_dict = sys.argv[3]
    except IndexError:
        print __doc__
        sys.exit()

    ## read dictionary files
    dict1 = read_dict(dict1)
    dict2 = read_dict(dict2)

    ## merge dictionaries and write new dictionary to file
    dict3 = merge_dicts(dict1, dict2)
    write_dict(merged_dict, dict3)
