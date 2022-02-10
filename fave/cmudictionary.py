#!/usr/bin/env python3
# *_* coding: utf-8 *_*

"""
Functions for working with CMU pronunciation dictionary
"""

__version__ = "2.0.0"
__author__ = ("Rosenfelder, Ingrid; " +  # Only code writers
              "Fruehwald, Josef; " +
              "Evanini, Keelan; " +
              "Seyfarth, Scott; " +
              "Gorman, Kyle; " +
              "Prichard, Hilary; " +
              "Yuan, Jiahong; " +
              "Brickhouse, Christian")
__email__ = "brickhouse@stanford.edu"
# should be the person who will fix bugs and make improvements
__maintainer__ = "Christian Brickhouse"
__copyright__ = "Copyright 2020, FAVE contributors"
__license__ = "GPLv3"
__status__ = "Development"  # Prototype, Development or Production
# also include contributors that wrote no code
__credits__ = ["Brandon Waldon"]

# --------------------------------------------------------------------------------

# Import built-in modules first
# followed by third-party modules
# followed by any changes to the path
# your own modules.

import re
import os
import logging


class CMU_Dictionary():
    """Representation of the CMU dictionary"""
    # beginning of uncertain transcription
    start_uncertain = re.compile(r'(\(\()')
    end_uncertain = re.compile(r'(\)\))')  # end of uncertain transcription
    truncated = re.compile(r'\w+\-$')  # truncated words
    # intended word (inserted by transcribers after truncated word)
    intended = re.compile(r'^\+\w+')
    ing = re.compile(r"IN'$")  # words ending in "in'"
    CONSONANTS = [
        'B',
        'CH',
        'D',
        'DH',
        'F',
        'G',
        'HH',
        'JH',
        'K',
        'L',
        'M',
        'N',
        'NG',
        'P',
        'R',
        'S',
        'SH',
        'T',
        'TH',
        'V',
        'W',
        'Y',
        'Z',
        'ZH']
    VOWELS = [
        'AA',
        'AE',
        'AH',
        'AO',
        'AW',
        'AY',
        'EH',
        'ER',
        'EY',
        'IH',
        'IY',
        'OW',
        'OY',
        'UH',
        'UW']
    # file for collecting uploaded additions to the dictionary
    DICT_ADDITIONS = "added_dict_entries.txt"
    STYLE_ENTRIES = [
        "R",
        "N",
        "L",
        "G",
        "S",
        "K",
        "T",
        "C",
        "WL",
        "MP",
        "SD",
        "RP"]

    def __init__(self, dictionary_file, **kwargs):
        """
        Initializes object by reading in CMU dictionary (or similar)

        Parameters
        ----------
        dictionary_file : string
            The full path to the location of a CMU-style dictionary.
        verbose : bool
            Whether to print debug information.
        prompt : bool
            Whether to prompt the user to fix errors.
        check : bool
            Whether this is an alignment or transcript check.
        """
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            format='%(levelname)s:%(message)s',
            level=kwargs['verbose'])

        self.__config_flags(**kwargs)

        self.dict_dir = dictionary_file
        self.cmu_dict = self.read(dictionary_file)
        # check that cmudict has entries
        if len(self.cmu_dict) == 0:
            self.logger.warning('Dictionary %s is empty', dictionary_file)
        self.logger.debug("End initialization.")

    def __config_flags(self, **kwargs):
        self.logger.debug('Reading config flags')
        self.verbose = False
        self.prompt = False
        self.check = False
        try:
            self.verbose = kwargs['verbose']
        except KeyError:
            self.logger.debug('No verbose argument; default to false.')
        try:
            self.prompt = kwargs['prompt']
        except KeyError:
            self.logger.debug('No prompt argument; default to false.')
        try:
            self.check = kwargs['check']
        except KeyError:
            self.logger.debug('No check argument; default to false.')

    def read(self, dictionary_file):
        """
        @author Keelan Evanini
        """
        self.logger.info(f'Reading dictionary from {dictionary_file}')
        cmu_dict = {}
        pat = re.compile('  *')  # two spaces separating CMU dict entries
        # CMU dictionary should be converted to a unicode format
        with open(dictionary_file, 'r', encoding="latin1") as cmu_dict_file:
            for line in cmu_dict_file.readlines():
                line = line.rstrip()
                line = re.sub(pat, ' ', line)  # reduce all spaces to one
                self.logger.debug(f'Dictionary line: {line}')
                word = line.split(' ')[0]  # orthographic transcription
                self.logger.debug(f'Word: {str(word)}')
                phones = line.split(' ')[1:]  # phonemic transcription
                self.logger.debug(f'Phones: {str(phones)}')
                if word not in cmu_dict:
                    cmu_dict[word] = []
                if phones not in cmu_dict[word]:
                    # add pronunciation to list of pronunciations
                    cmu_dict[word].append(phones)
        return cmu_dict

    def add_dictionary_entries(self, infile, path='.'):
        """
        Reads additional dictionary entries from file and adds them to the CMU dictionary

        @param string infile
        @param string path
        @raises IndexError
        """

        cmu_dict = self.cmu_dict
        add_dict = {}

        with open(infile, 'r') as f:
            lines = f.readlines()

        # process entries
        for line in lines:
            try:
                columns = line.strip().split('\t')
                word = columns[0].upper()
                transcriptions = [
                    self.check_transcription(
                        t.strip()) for t in columns[1].replace(
                            '"', '').split(',')]
                if len(transcriptions) == 0:
                    continue
            except IndexError as err:
                self.logger.error(
                    f"Incorrect format of dictionary input file {infile}: {line}")
                raise ValueError('Incorrect dictionary input file') from err
            # add new entry to CMU dictionary
            if word not in cmu_dict:
                cmu_dict[word] = transcriptions
                add_dict[word] = transcriptions
                # word might be in dict but transcriber might want to add
                # alternative pronunciation
            else:
                for t in transcriptions:
                    # check that new transcription is not already in dictionary
                    if t not in cmu_dict[word]:
                        cmu_dict[word].append(t)
                    if word not in add_dict:
                        add_dict = []
                    if t not in add_dict[word]:
                        add_dict[word].append(t)

        if self.verbose:
            self.logger.debug(
                "Added all entries in file %s to CMU dictionary.",
                os.path.basename(infile))

        # add new entries to the file for additional transcription entries
        # (merge with the existing DICT_ADDITIONS file to avoid duplicates)
        added_items_file = os.path.join(path, self.DICT_ADDITIONS)
        if os.path.exists(
                added_items_file):  # check whether dictionary additions file exists already
            added_already = self.read(added_items_file)
            new_dict = self.merge_dicts(added_already, add_dict)
        else:
            new_dict = add_dict
        self.write_dict(added_items_file, dictionary=new_dict)
        if self.verbose:
            self.logger.debug(
                "Added new entries from file %s to file %s.",
                os.path.basename(infile), self.DICT_ADDITIONS)

    def check_transcription(self, transcription):
        """checks that the transcription entered for a word conforms to the Arpabet style"""
        # INPUT:  string w = phonetic transcription of a word (phones should be separated by spaces)
        # OUTPUT:  list final_trans = list of individual phones (upper case,
        # checked for correct format)

        # convert to upper case and split into phones
        phones = transcription.upper().split()

        # check that phones are separated by spaces
        # (len(w) > 3:  transcription could just consist of a single phone!)
        if len(transcription) > 3 and len(phones) < 2:
            p = (
                "Something is wrong with your transcription:  %s.\n" %
                transcription)
            self.logger.warning(p)
            # Maybe worth raising an exception if self.prompt == False
            if self.prompt:
                p += "Did you forget to enter spaces between individual phones?\n"
                p += "Please enter new transcription:  "
                new_trans = input(p)
                transcription = self.check_transcription(new_trans)
        else:
            for index, phone in enumerate(phones):
                try:
                    self.check_phone(phone, transcription, index)
                except ValueError as err:
                    raise err
        return transcription

    def check_phone(self, phone, transcription, index):
        """checks that a phone entered by the user is part of the Arpabet"""
        # INPUT:
        # string p = phone
        # string w = word the contains the phone (normal orthographic representation)
        # int i = index of phone in word (starts at 0)
        # OUTPUT:
        # string final_p or p = phone in correct format
        if len(phone) == 3:
            if str(phone[-1]) not in ['0', '1', '2']:
                self.logger.error(
                    "Unknown stress %s for vowel %s in word %s", phone[-1], phone, transcription)
                raise ValueError("Unknown stress digit")
            if phone[:-1] not in self.VOWELS:
                raise ValueError("Unknown vowel %s (at position %i) in word %s!\n" % (
                    phone[:-1], index + 1, transcription))
        elif len(phone) <= 2:
            if phone in self.VOWELS:
                raise ValueError(
                    "You forgot to enter the stress digit for vowel %s (at position %i) in word %s!\n" %
                    (phone, index + 1, transcription))
            if phone not in self.CONSONANTS:
                raise ValueError(
                    "Unknown phone %s (at position %i) in word %s!\n" %
                    (phone, index + 1, transcription))
        else:
            raise ValueError(
                "Unknown phone %s (at position %i) in word %s!\n" %
                (phone, index + 1, transcription))

    def __check_word(self, word, next_word):
        """A rewrite of check word
        returns bool
        """

        if word.upper() in self.cmu_dict:
            return True
        self.logger.debug(f'Cannot find {word} in dictionary')
        if self.intended.search(next_word):
            self.logger.debug(f'Hint given: {next_word}')
            if next_word in self.cmu_dict:
                self.logger.debug('Clue is in dictionary')
                # pylint: disable=no-else-return
                if self.check:
                    self.logger.debug(
                        'Running in check mode, returning false so transcript can be checked')
                    return False
                else:
                    return True
        self.logger.debug('No hint given')
        return False

    def check_word(self, word, next_word='', unknown=None, line=''):
        """checks whether a given word's phonetic transcription is in the CMU dictionary;
        adds the transcription to the dictionary if not"""
        # INPUT:
        # string word = word to be checked
        # string next_word = following word
        # OUTPUT:
        # dict unknown = unknown or truncated words (needed if "check transcription" option is selected; remains empty otherwise)
        # - modifies CMU dictionary (dict cmudict)
        if not isinstance(unknown, dict):
            unknown = {}

        self.logger.debug(f'Checking if \'{word}\' in dictionary')
        inDict = bool(self.__check_word(word, next_word))

        cmudict = self.cmu_dict
        clue = next_word.strip().lstrip('+').upper()

        if not inDict and word not in self.STYLE_ENTRIES:
            # don't do anything if word itself is a clue word
            if '+' in word:
                return unknown
            # don't do anything for unclear transcriptions:
            if word == '((xxxx))':
                return unknown
            # uncertain transcription:
            if self.start_uncertain.search(
                    word) or self.end_uncertain.search(word):
                if self.start_uncertain.search(
                        word) and self.end_uncertain.search(word):
                    word = word.replace('((', '')
                    word = word.replace('))', '')
                    # check if word is in dictionary without the parentheses
                    if not self.__check_word(word, ''):
                        return unknown
                else:  # This should not happen!
                    error = "ERROR!  Something is wrong with the transcription of word %s!" % word
                    raise ValueError(error)
            # asterisked transcriptions:
            elif word[0] == "*":
                # check if word is in dictionary without the asterisk
                if not self.__check_word(word[1:], ''):
                    return unknown
            # generate new entries for "-in'" words
            if word[-3:].upper() == "IN'":
                gword = word[:-1].upper() + 'G'
                # if word has entry/entries for corresponding "-ing" form:
                if self.__check_word(gword, ''):
                    for t in cmudict[gword]:
                        # check that transcription entry ends in "- IH0 NG":
                        if t[-2:] == ["IH0", "NG"]:
                            new_transcription = t[:-2]
                            new_transcription[-2] = "AH0"
                            new_transcription[-1] = "N"
                            if not inDict:
                                self.cmu_dict[word] = []
                            if new_transcription not in cmudict[gword]:
                                self.cmu_dict[word].append(new_transcription)
                    return unknown
            # if "check transcription" option is selected, add word to list of
            # unknown words
            if not inDict:
                if self.check:
                    self.logger.info(f"Unknown word '{word}'")
                else:
                    self.logger.warning(f"Unknown word '{word}'")
                unknown[word] = ("", clue.lstrip('+'), line)
                return unknown
        if word in self.STYLE_ENTRIES:
            self.logger.info(f"Style entry: {word}")
        elif inDict:
            self.logger.debug("Entry found")
        else:
            self.logger.warning(f"No transcription for '{word}'")
        return unknown

    @staticmethod
    def merge_dicts(d1, d2):
        """merges two versions of the CMU pronouncing dictionary"""
        # for each word, each transcription in d2, check if present in d1
        for word in d2:
            # if no entry in d1, add entire entry
            if word not in d1:
                d1[word] = d2[word]
            # if entry in d1, check whether additional transcription variants
            # need to be added
            else:
                for t in d2[word]:
                    if t not in d1[word]:
                        d1[word].append(t)
        return d1

    def write_dict(self, fname, dictionary=None):
        """writes the new version of the CMU dictionary (or any other dictionary) to file"""

        # default functionality is to write the CMU pronunciation dictionary back to file,
        # but other dictionaries or parts of dictionaries can also be
        # written/appended
        if not dictionary:
            dictionary = self.cmu_dict
        out_string = ''
        # sort dictionary before writing to file
        keys = sorted(dictionary)
        # self.logger.debug(keys)
        for word in keys:
            # make a separate entry for each pronunciation in case of
            # alternative entries
            if len(dictionary[word]) < 1:
                continue
            for transcription in dictionary[word]:
                # two spaces separating CMU dict entries from phonetic
                # transcriptions
                out_string += word + '  '
                for phone in transcription:
                    out_string += phone + ' '  # list of phones, separated by spaces
                out_string += '\n'  # end of entry line

        with open(fname, 'w') as f:
            f.write(out_string)

    @staticmethod
    def _write_words(unknown):
        """writes unknown words to file (in a specified encoding)"""
        out_string = ''
        for w in unknown:
            out_string += w + '\t'
            if unknown[w][0]:
                # put suggested transcription(s) for truncated word into second
                # column, if present:
                out_string += ','.join([' '.join(i) for i in unknown[w][0]])
            out_string += '\t'
            if unknown[w][1]:
                # put following clue word in third column, if present:
                out_string += unknown[w][1]
            # put line in fourth column:
            out_string += '\t' + unknown[w][2] + '\n'
        return out_string

    def write_unknown_words(self, unknown, fname="unknown.txt"):
        """writes the list of unknown words to file"""
        with open(fname, 'w') as f:
            f.write(self._write_words(unknown))

#
# !!! This is NOT the original cmu.py file !!!             ##
#
# Last modified by Ingrid Rosenfelder:  April 6, 2010                ##
# - all comments beginning with double pound sign ("##")             ##
# - (comment before read_dict(f) deleted)                            ##
# - docstrings for all classes and functions                         ##
#


import re


class Phone:

    """represents a CMU dict phoneme (label and distinctive features)"""
    # !!! not to be confused with class extractFormants.Phone !!!
    label = ''  # label
    vc = ''  # vocalic (+ = vocalic, - = consonantal)
    vlng = ''  # vowel length (l = long, s = short, d = diphthong, a = ???, 0 = n/a)
    vheight = ''  # vowel height (1 = high, 2 = mid, 3 = low)
    vfront = ''  # vowel frontness (1 = front, 2 = central, 3 = back)
    vrnd = ''  # vowel roundness (+ = rounded, - = unrounded, 0 = n/a)
    ctype = ''  # manner of articulation (s = stop, a = affricate, f = fricative, n = nasal, l = lateral, r = glide, 0 = n/a)
    cplace = ''  # place of articulation (l = labial, b = labiodental, d = dental, a = apical, p = palatal, v = velar, 0 = n/a)
    cvox = ''  # consonant voicing (+ = voiced, - = unvoiced, 0 = n/a)


def read_dict(f):
    """reads the CMU dictionary and returns it as dictionary object,
    allowing multiple pronunciations for the same word"""
    dictfile = open(f, 'r')
    lines = dictfile.readlines()
    dict = {}
    pat = re.compile('  *')  # two spaces separating CMU dict entries
    for line in lines:
        line = line.rstrip()
        line = re.sub(pat, ' ', line)  # reduce all spaces to one
        word = line.split(' ')[0]  # orthographic transcription
        phones = line.split(' ')[1:]  # phonemic transcription
        if word not in dict:
            dict[word] = [phones]
                # phonemic transcriptions represented as list of lists of
                # phones
        else:
            dict[word].append(
                phones)  # add alternative pronunciation to list of pronunciations
    dictfile.close()
    return dict


def read_phoneset(f):
    """reads the CMU phoneset (assigns distinctive features to each phoneme);
      returns it as dictionary object"""
    lines = open(f, 'r').readlines()
    phoneset = {}
    for line in lines[1:]:  # leave out header line
        p = Phone()
        line = line.rstrip('\n')
        label = line.split()[0]  # phoneme label
        p.label = label
        p.vc = line.split()[1]  # vocalic
        p.vlng = line.split()[2]  # vowel length
        p.vheight = line.split()[3]  # vowel height
        p.vfront = line.split()[4]  # vowel frontness
        p.vrnd = line.split()[5]  # vowel roundness
        p.ctype = line.split()[6]  # consonants:  manner of articulation
        p.cplace = line.split()[7]  # consonants:  place of articulation
        p.cvox = line.split()[8]  # consonants:  voicing
        phoneset[label] = p
    return phoneset
