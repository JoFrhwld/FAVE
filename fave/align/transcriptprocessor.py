#!/usr/bin/env python3
# *_* coding: utf-8 *_*

"""
Functions for processing FAAV transcripts
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
import sys
import os
import logging
from fave import cmudictionary


class TranscriptProcessor():
    """Wrapper for handling tab delimited FAAV transcription files"""
    # beginning of uncertain transcription
    start_uncertain = re.compile(r'(\(\()')
    end_uncertain = re.compile(r'(\)\))')  # end of uncertain transcription
    hyphenated = re.compile(r'(\w+)-(\w+)')  # hyphenated words
    # intended word (inserted by transcribers after truncated word)
    intended = re.compile(r'^\+\w+')
    # uncertain transcription (single word)
    uncertain = re.compile(r"\(\(([\*\+]?['\w]+\-?)\)\)")
    # NOTE:  earlier versions allowed uncertain/unclear transcription to use only one parenthesis,
    # but this is now back to the strict definition
    # (i.e. uncertain/unclear transcription spans MUST be enclosed in DOUBLE parentheses)
    # unclear transcription (empty double parentheses)
    unclear = re.compile(r'\(\(\s*\)\)')

    def __init__(
            self,
            transript_file,
            pronunciation_dictionary,
            *args,
            **kwargs
    ):
        # "flag_uncertain" indicates whether we are currently inside an
        # uncertain section of transcription (switched on and off by the
        # beginning or end of double parentheses:  "((", "))")
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            format='%(levelname)s:%(message)s',
            level=kwargs['verbose'])

        self.file = transript_file
        self.__config_flags(**kwargs)

        self.flag_uncertain = False
        self.last_beg_uncertain = ''
        self.last_end_uncertain = ''
        self.temp_dict_dir = None
        self.lines = []
        self.trans_lines = []
        self.delete_lines = None
        if not isinstance(
                pronunciation_dictionary,
                cmudictionary.CMU_Dictionary):
            raise ValueError(
                'pronunciation_dictionary must be a CMU_Dictionary object')
        self.dictionary = pronunciation_dictionary

    def __config_flags(self, **kwargs):
        self.prompt = kwargs['prompt']
        if kwargs['check']:
            self.unknownFile = kwargs['check']
        self.check = bool(kwargs['check'])

    def check_dictionary_entries(self, wavfile):
        """checks that all words in lines have an entry in the CMU dictionary;
        if not, prompts user for Arpabet transcription and adds it to the dict
        file. If "check transcription" option is selected, writes list of
        unknown words to file and exits."""
        # INPUT:  list of lines to check against CMU dictionary
        # OUTPUT:  list newlines = list of list of words for each line (processed)
        # - prompts user to modify CMU dictionary (cmudict) and writes updated
        #           version of CMU dictionary to file
        # - if "check transcription" option is selected, writes list of unknown
        #       words to file and exits
        self.logger.debug('Checking dictionary entries')
        newlines = []
        unknown = {}

        for line in self.trans_lines:
            newwords = []
            # get list of preprocessed words in each line
            # This may lead to a race condition -CB
            words = self.preprocess_transcription(line.strip().upper())
            # check each word in transcription as to whether it is in the CMU dictionary:
            # (if "check transcription" option is not set, dict unknown will simply remain empty)
            for i, w in enumerate(words):
                if i < len(words) - 1:
                    unknown = self.dictionary.check_word(
                        w, words[i + 1], unknown, line)
                else:
                    unknown = self.dictionary.check_word(
                        w, '', unknown, line)  # last word in line
                # take "clue words" out of transcription:
                if not self.intended.search(self.uncertain.sub(r'\1', w)):
                    newwords.append(w)
            newlines.append(newwords)

        # write new version of the CMU dictionary to file
        # (do this here so that new entries to dictionary will still be saved
        # if "check transcription" option is selected
        # in addition to the "import transcriptions" option)
        # write_dict(options.dict)
        # NOTE:  dict will no longer be re-written to file as people might
        # upload all kinds of junk. Uploaded additional transcriptions will
        # be written to a separate file instead (in add_dictionary_entries),
        # to be checked manually and merged with the main dictionary at certain
        # intervals

        # write temporary version of the CMU dict to file for use in alignment
        if not self.check:
            temp_dict = os.path.join(
                os.path.dirname(wavfile), '_'.join(
                    os.path.basename(wavfile).split('_')[
                        :2]) + "_" + "dict")
            self.logger.debug(f"temp_dict is {temp_dict}")
            self.dictionary.write_dict(temp_dict)
            self.logger.debug(
                    "Written updated temporary version of CMU dictionary.")
            # forced alignment must use updated cmudict, not original one
            self.temp_dict_dir = temp_dict

        # "CHECK TRANSCRIPTION" OPTION:
        # write list of unknown words and suggested transcriptions for
        # truncated words to file
        if self.check:
            self.dictionary.write_unknown_words(unknown,self.unknownFile)
            self.logger.info(
                "Written list of unknown words in transcription to file %s.",
                self.unknownFile)
            if __name__ == "__main__":
                sys.exit()  # It shouldn't just die, but return and clean up after itself

        # CONTINUE TO ALIGNMENT:
        else:
            # return new transcription (list of lists of words, for each line)
            self.trans_lines = newlines

    def preprocess_transcription(self, line):
        """preprocesses transcription input for CMU dictionary lookup and forced alignment"""
        # INPUT:  string line = line of orthographic transcription
        # OUTPUT:  list words = list of individual words in transcription

        self.logger.debug("Preprocessing transcript line:")
        self.logger.debug(f"    {line}")
        flag_uncertain = self.flag_uncertain
        last_beg_uncertain = self.last_beg_uncertain
        last_end_uncertain = self.last_end_uncertain

        original_line = line

        # make "high school" into one word (for /ay0/ raising)
        line = line.replace('high school', 'highschool')

        # make beginning and end of uncertain transcription spans into separate
        # words
        line = self.start_uncertain.sub(r' (( ', line)
        line = self.end_uncertain.sub(r' )) ', line)
        # correct a common transcription error (one dash instead of two)
        line = line.replace(' - ', ' -- ')
        # delete punctuation marks
        for p in [',', '.', ':', ';', '!', '?', '"', '%', '--']:
            line = line.replace(p, ' ')
        # delete initial apostrophes
        line = re.compile(r"(\s|^)'\b").sub(" ", line)
        # delete variable coding for consonant cluster reduction
        line = re.compile(r"\d\w(\w)?").sub(" ", line)
        # replace unclear transcription markup (empty parentheses):
        line = self.unclear.sub('((xxxx))', line)
        # correct another transcription error:  truncation dash outside of
        # double parentheses will become a word
        line = line.replace(' - ', '')

        # split hyphenated words (but keep truncated words as they are!)
        # NOTE:  This also affects the interjections "huh-uh", "uh-huh" and "uh-oh".
        # However, should work fine just aligning individual components.
        line = self.hyphenated.sub(r'\1 \2', line)
        # do this twice for words like "daughter-in-law"
        line = self.hyphenated.sub(r'\1 \2', line)

        # split line into words:
        words = line.split()
        self.logger.debug(words)

        # add uncertainty parentheses around every word individually
        newwords = []
        for word in words:
            self.logger.debug(word)
            self.logger.debug(flag_uncertain)
            if word == "((":  # beginning of uncertain transcription span
                if not self.flag_uncertain:
                    self.flag_uncertain = True
                    self.last_beg_uncertain = original_line
                else:
                    msg = "Beginning of uncertain transcription span detected twice in a row\n"
                    msg += (
                        "Please close the the opening double parenthesis in line '%s'" %
                        last_beg_uncertain)
                    raise ValueError(msg)
                continue
            if word == "))":  # end of uncertain transcription span
                if self.flag_uncertain:
                    self.flag_uncertain = False
                    self.last_end_uncertain = original_line
                else:
                    msg = "End of uncertain transcription span detected twice in a row\n"
                    msg += "No opening double parentheses for line %s." % last_end_uncertain
                    raise ValueError(msg)
                continue
            if self.flag_uncertain:
                newwords.append("((" + word + "))")
            else:
                newwords.append(word)

        return newwords

    def read_transcription_file(self):
        """Reads file into memory"""
        with open(self.file) as f:
            lines = self.replace_smart_quotes(f.readlines())
        self.lines = lines

    # substitute any 'smart' quotes in the input file with the corresponding
    # ASCII equivalents (otherwise they will be excluded as out-of-
    # vocabulary with respect to the CMU pronouncing dictionary)
    # WARNING: this function currently only works for UTF-8 input
    @staticmethod
    def replace_smart_quotes(all_input):
        """Replace fancy quotes with straight quotes"""
        cleaned_lines = []
        for line in all_input:
            line = line.replace(u'\u2018', "'")
            line = line.replace(u'\u2019', "'")
            line = line.replace(u'\u201a', "'")
            line = line.replace(u'\u201b', "'")
            line = line.replace(u'\u201c', '"')
            line = line.replace(u'\u201d', '"')
            line = line.replace(u'\u201e', '"')
            line = line.replace(u'\u201f', '"')
            cleaned_lines.append(line)
        return cleaned_lines

    def check_transcription_file(self):
        """checks the format of the input transcription file and returns a
        list of empty lines to be deleted from the input
        """
        all_input = self.lines
        trans_lines = []
        delete_lines = []
        for line in all_input:
            t_entries, d_line = self.check_transcription_format(line)
            if t_entries:
                trans_lines.append(t_entries[4])
            if d_line:
                delete_lines.append(d_line)
        self.trans_lines = trans_lines
        self.delete_lines = delete_lines

    @staticmethod
    def check_transcription_format(line):
        """checks that input format of transcription file is correct
        (5 tab-delimited data fields)
        """
        # INPUT:  string line = line of transcription file
        # OUTPUT: list entries = fields in line (speaker ID and name,
        #                        begin and end times, transcription text)
        # string line = empty transcription line to be deleted

        if line.strip() == '':
            return None, line

        entries = line.rstrip().split('\t')
        if len(entries) != 5:
            error = ("Incorrect format of transcription file: %i entries per line in line %s.",
                     len(entries), line.rstrip())
            raise ValueError(error)
        return entries, None
