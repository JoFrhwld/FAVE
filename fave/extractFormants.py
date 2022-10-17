#!/usr/bin/env python

#
# !!! This is NOT the original extractFormants.py file !!!              ##
#
# - all comments beginning with a double pound sign ("##")                    ##
# - docstrings for all classes and functions                                  ##
# - alphabetic ordering outside of main program:                              ##
# 1. classes                                                             ##
# 2. functions                                                           ##
# - allow multiple speakers in input TextGrids                                ##
# - user prompted for speaker info                                            ##
# - excluded from analysis:                                                   ##
# - uncertain and unclear transcriptions                                 ##
# - overlaps                                                             ##
# - last syllables of truncated words                                    ##
# - entries on style tier added to vowel measurements                         ##
# - boolean options (instead of 'T', 'F')                                     ##
# - poles and bandwidths as returned by LPC analysis added to output          ##
# - Mahalanobis distance takes formant settings from options/defaults         ##
# - speakers' last names optional                                             ##
# - fixed rounding problem with phone duration (< 50 ms)                      ##
# - changed Praat Formant method to Burg for Mahalanobis measurement method   ##
# - adapted Mahalanobis method to vary number of formants from 3 to 6 (Burg), ##
# then choose winning pair from all F1/F2 combinations of these             ##
# - changed Praat object from` LPC to Formant                                  ##
# - no restriction on # of formants per frame for Formant objects             ##
# - smoothing of formant tracks ( -> parameter nSmoothing in options)         ##
# - FAAV measurement procedure:                                               ##
# - AY has 50 ms left padding and is measured at maximum F1              ##
# - Tuw measured at beginning of segment                                 ##
# - OW, AW measured halfway between beginning of segment and F1 maximum  ##
# - EY is measured at maximum F1, but without extra padding              ##
# - returns F3 and corresponding bandwidth, if possible                       ##
# - outputs and summarizes chosen nFormants (in separate file)                ##
# - integrated remeasurement.py                                               ##
# - new options:  remeasurement and candidates                                ##
# - fixed checkTextGrid so that compatible with FA online interface output    ##
# - added ethnicity and location to speaker object & changed output file      ##
# - added "both" as output option (writes Plotnik file AND text file)         ##
# - added "--speaker=speakerfile" option                                      ##
# - added normalization and calculation of means for each vowel class         ##
# - corrected anae() method index error                                       ##
# - added phila_system as separate option (no longer dependent on file name)  ##
# - changed "phila_system" option to "vowelSystem" to allow multiple values:  ##
# - "Phila"                                                              ##
# - "NorthAmerican" (default)                                            ##
# - "simplifiedARPABET"                                                  ##
# - fixed interference between minimum vowel length and smoothing window      ##
# - added output of formant "tracks" (formant measurements at 20%, 35%, 50%,  ##
# 65% and 80% of the vowel duration) in angular brackets in Plotnik files   ##
# - fixed floating point problem of minimum duration in getTransitionLength   ##
# - fixed errors caused by gaps in the vowel wave forms (at measurement point)##
#
#


"""
Takes as input a sound file and a Praat .TextGrid file (with word and phone tiers)
and outputs automatically extracted F1 and F2 measurements for each vowel
(either as a tab-delimited text file or as a Plotnik file).
"""


import sys
import os
import shutil
import argparse
import math
import re
import time
import pkg_resources
import csv
import pickle
import subprocess
from itertools import tee, islice
from bisect import bisect_left

import numpy as np

from tqdm import tqdm

import fave
from fave.extract import esps
from fave.extract import plotnik
from fave.extract import vowel
from fave import praat
from fave import cmudictionary as cmu
from fave.extract.remeasure import remeasure
from fave.extract.mahalanobis import mahalanobis

SCRIPTS_HOME = pkg_resources.resource_filename('fave','praatScripts')
os.chdir(os.getcwd())

uncertain = re.compile(r"\(\(([\*\+]?['\w]+\-?)\)\)")

CONSONANTS = ['B', 'CH', 'D', 'DH', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M',
              'N', 'NG', 'P', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'Y', 'Z', 'ZH']
VOWELS = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH',
          'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
SPECIAL = ['BR', 'CG', 'LS', 'LG', 'NS']


#

class Phone:

    """represents a single phone (label, times and Plotnik code (for vowels))"""
    # !!! not the same as class cmu.Phone !!!

    def __init__(self):
        self.label = ''  # phone label (Arpabet coding)
        self.code = ''  # Plotnik vowel code ("xx.xxxxx")
        self.xmin = None  # beginning of phone
        self.xmax = None  # end of phone
        self.cd = ''  # Plotnik code:  vowel class
        self.fm = ''  # Plotnik code:  following segment - manner
        self.fp = ''  # Plotnik code:  following segment - place
        self.fv = ''  # Plotnik code:  following segment - voice
        self.ps = ''  # Plotnik code:  preceding segment
        self.fs = ''  # Plotnik code:  following sequences
        self.overlap = False
        self.pp = None  # preceding phone (Arpabet label)
        self.arpa = ''  # Arpabet coding WITHOUT stress digit
        self.stress = None  # stress digit


class Speaker:

    """represents a speaker (background info)"""

    def __init__(self):
        self.name = ''
        self.first_name = ''
        self.last_name = ''
        self.age = ''
        self.sex = ''
        self.ethnicity = ''
        self.years_of_schooling = ''
        self.location = ''
        self.city = ''  # 'Philadelphia'
        self.state = ''  # 'PA'
        self.year = ''  # year of recording
        self.tiernum = None  # tiernum points to phone tier = first tier for given speaker


class VowelMeasurement:

    """represents a vowel measurement"""
    # !!! not the same as class plotnik.VowelMeasurement !!!

    def __init__(self):
        self.phone = ''  # Arpabet coding
        self.stress = ''  # stress level ("1", "2", "0")
        self.style = ''  # style label (if present)
        self.word = ''  # corresponding word
        self.f1 = None  # first formant
        self.f2 = None  # second formant
        self.f3 = None  # third formant
        self.b1 = None  # bandwidth of first formant
        self.b2 = None  # bandwidth of second formant
        self.b3 = None  # bandwidth of third formant
        self.t = ''  # time of measurement
        self.code = ''  # Plotnik vowel code ("xx.xxxxx")
        self.cd = ''  # Plotnik code for vowel class
        self.fm = ''  # Plotnik code for manner of following segment
        self.fp = ''  # Plotnik code for place of following segment
        self.fv = ''  # Plotnik code for voicing of following segment
        self.ps = ''  # Plotnik code for preceding segment
        self.fs = ''  # Plotnik code for following sequences
        self.text = ''  # ???
        self.beg = None  # beginning of vowel
        self.end = None  # end of vowel
        self.dur = None  # duration of vowel
        self.poles = []  # original list of poles returned by LPC analysis
        self.bandwidths = []
            # original list of bandwidths returned by LPC analysis
        self.times = []
        self.winner_poles = []
        self.winner_bandwidths = []
        self.all_poles = []
        self.all_bandwidths = []
        self.nFormants = None  # actual formant settings used in the measurement (for Mahalanobis distance method)
        self.glide = ''  # Plotnik glide coding
        self.norm_f1 = None  # normalized F1
        self.norm_f2 = None  # normalized F2
        self.norm_f3 = None  # normalized F3
        self.tracks = []
            # formant "tracks" (five sample points at 20%, 35%, 50%, 65% and
            # 80% of the vowel)
        self.all_tracks = []
            # formant "tracks" for all possible formant settings (needed for
            # remeasurement)
        self.norm_tracks = []  # normalized formant "tracks"
        self.pre_seg = ''
        self.fol_seg = ''
        self.context = ''
        self.p_index = ''
        self.word_trans = ''
        self.pre_word_trans = ''
        self.fol_word_trans = ''
        self.pre_word = ''
        self.fol_word = ''

class VowelMean:

    """represents the mean and standard deviation for a given vowel class"""

    def __init__(self):
        self.pc = ''  # Plotnik vowel class
        self.means = ['', '', '']  # means for F1, F2, F3
        self.stdvs = ['', '', '']  # standard deviations for F1, F2, F3
        self.n = [0, 0, 0]
            # number of tokens used to calculate means and standard deviations
        self.values = [[], [], []]  # formant values from individual tokens
        self.norm_means = ['', '', '']  # normalized means
        self.norm_stdvs = ['', '', '']  # normalized standard deviations
        self.trackvalues = []
            # formant "tracks" (5 measurement points) from individual tokens
        self.trackmeans = []  # means values for formant "tracks"
        self.trackmeans_norm = []  # normalized mean formant "tracks"

    def __str__(self):
        return '<Means for vowel class %s:  means=%s, stdvs=%s, tokens=%s,\nnormalized:  means=%s, stdvs=%s, values:\n\tF1:  %s,\n\tF2:  %s,\n\tF3:  %s>' % (self.pc, self.means, self.stdvs, self.n, self.norm_means, self.norm_stdvs, self.values[0], self.values[1], self.values[2])


class Word:

    """represents a word (transcription, times and list of phones)"""

    def __init__(self):
        self.transcription = ''  # transcription
        self.phones = []  # list of phones
        self.xmin = None  # beginning of word
        self.xmax = None  # end of word
        self.style = ''  # style label (if present)

#


def addOverlaps(words, tg, speaker):
    """for a given speaker, checks each phone interval against overlaps on other tiers"""

    # NOTE:  this thing can really slow down the program if you're checking some 20,000 phone intervals...
    # -> use of pointers speeds up this part of the program by a factor of 18 or so :-)

    # initialize pointers
    pointer = []
    for r in range(len(tg) // 2):
        pointer.append(0)
    # check all vowel phones in speaker's word list
    for w in words:
        for p in w.phones:
            # don't bother checking for overlaps for consonants (speeds up the
            # program)
            if isVowel(p.label):
                # check all other (word) tiers if corresponding interval is non-empty
                # (word tiers vs. interval tiers:  speeds up program by a factor of 2-2.5)
                for sn in range(len(tg) // 2):  # sn = speaknum!
                    if (sn * 2) != speaker.tiernum:
                        # go up to last interval that overlaps with p
                        while pointer[sn] < len(tg[sn * 2 + 1]) and tg[sn * 2 + 1][pointer[sn]].xmin() < p.xmax:
                            # current interval for comparison
                            i = tg[sn * 2 + 1][pointer[sn]]
                            # if boundaries overlap and interval not empty
                            if ((((i.xmin() <= p.xmin) or (p.xmin <= i.xmin() <= p.xmax))
                                and ((i.xmax() >= p.xmax) or (p.xmin <= i.xmax() <= p.xmax)))
                                    and not i.mark().upper() in ["SP","sil",""]):
                                p.overlap = True
                            pointer[sn] += 1
                        # go back one interval, since the last interval needs
                        # to be checked again for the next phone
                        pointer[sn] -= 1

    return words


def addPlotnikCodes(words, phoneset, speaker, vowelSystem):
    """takes a list of words and adds Plotnik codes to the vowels"""

    for w in words:
        n = getNumVowels(w)
        if n == 0:
            continue
        for i in range(len(w.phones)):
            if isVowel(w.phones[i].label):
                code, prec_p = plotnik.cmu2plotnik_code(i, w.phones, w.transcription, phoneset, speaker, vowelSystem)
                if code:  # no code returned if it's a consonant
                    w.phones[i].code = code  # whole code
                    w.phones[i].cd = code.split('.')[0]  # vowel class code
                    w.phones[i].fm = code.split('.')[1][0]  # following segment - manner
                    w.phones[i].fp = code.split('.')[1][1]  # following segment - place
                    w.phones[i].fv = code.split('.')[1][2]  # following segment - voice
                    w.phones[i].ps = code.split('.')[1][3]  # preceding segment
                    w.phones[i].fs = code.split('.')[1][4]  # following sequences
                if (prec_p and prec_p != '') or prec_p == '':  # phone is a vowel and has or has not preceding segment
                    w.phones[i].pp = prec_p

    return words

def addStyleCodes(words, tg):
    """copies coding from style tier to each word"""

    i_start = 0  # start interval on style tier
    for w in words:
        # iterate over the style tier from approximately the point where the
        # style code for the last word was found
        for i, s in enumerate(tg[-1][i_start:]):
            # break off style tier iteration after the end of the word
            if s.xmin() >= w.xmax:
                # set new start interval (NOTE:  i starts counting from the
                # previous i_start!)
                i_start += i - \
                    2  # start next iteration two intervals before, just in case
                if i_start < 0:
                    i_start = 0  # keep i_start >= 0
                break
            # add style code, if style code interval overlaps with the word
            if s.mark().upper() != "SP":
                if ((s.xmin() <= w.xmin <= s.xmax() and s.xmin() <= w.xmax <= s.xmax())  # "perfect" case:  entire word contained in style tier interval
                    or (w.xmin <= s.xmin() and s.xmin() <= w.xmax <= s.xmax())  # word shifted to the left relative to style tier interval
                    or (s.xmin() <= w.xmin <= s.xmax() and s.xmax() <= w.xmax)  # word shifted to the right relative to style tier interval
                        or (w.xmin <= s.xmin() and s.xmax() <= w.xmax)):  # "worst" case:  word interval contains style tier interval
                    w.style = s.mark().upper()
                    # set new start interval (NOTE:  i starts counting from the
                    # previous i_start!)
                    i_start += i - 1  # start one interval before, just in case
                    if i_start < 0:
                        i_start = 0  # keep i_start >= 0
                    break

    return words


def anae(v, formants, times):
    """returns time of measurement according to the ANAE (2006) guidelines"""

    F1 = [f[0] if len(f) >= 1 else None for f in formants]
                      # NOTE:  'None' elements in the two formant lists are
                      # needed
    F2 = [f[1] if len(f) >= 2 else None for f in formants]
                      # to preserve the alignment with the 'times' list!
    # measure at F1 maximum, except for "AE" or "AO"
    if v == 'AE':
        i = F2.index(max(F2))
    elif v == 'AO':
        i = F2.index(min(F2))
    else:
        i = F1.index(max(F1))
    measurementPoint = times[i]

    return measurementPoint


def calculateMeans(measurements):
    """takes a list of vowel measurements and calculates the means for each vowel class"""

    # initialize vowel means
    means = {}
    for p in plotnik.PLOTNIKCODES:
        newmean = VowelMean()
        newmean.pc = p
        means[p] = newmean
    # process measurements
    for m in measurements:
        # only include tokens with primary stress
        if m.stress != '1':
            continue
        # exclude tokens with F1 < 200 Hz
        if m.f1 < 200:
            continue
        # exclude glide measurements
        if m.glide == 'g':
            continue
        # exclude function words
        if m.word.upper() in ['A', 'AH', 'AM', "AN'", 'AN', 'AND', 'ARE', "AREN'T", 'AS', 'AT', 'AW', 'BECAUSE', 'BUT', 'COULD',
              'EH', 'FOR', 'FROM', 'GET', 'GONNA', 'GOT', 'GOTTA', 'GOTTEN',
              'HAD', 'HAS', 'HAVE', 'HE', "HE'S", 'HIGH', 'HUH',
              'I', "I'LL", "I'M", "I'VE", "I'D", 'IN', 'IS', 'IT', "IT'S", 'ITS', 'JUST', 'MEAN', 'MY',
              'NAH', 'NOT', 'OF', 'OH', 'ON', 'OR', 'OUR', 'SAYS', 'SHE', "SHE'S", 'SHOULD', 'SO',
              'THAN', 'THAT', "THAT'S", 'THE', 'THEM', 'THERE', "THERE'S", 'THEY', 'TO', 'UH', 'UM', 'UP',
              'WAS', "WASN'T", 'WE', 'WERE', 'WHAT', 'WHEN', 'WHICH', 'WHO', 'WITH', 'WOULD',
              'YEAH', 'YOU', "YOU'VE"]:
            continue
        # exclude /ae, e, i, aw/ before nasals
        if m.cd in ['3', '2', '1', '42'] and m.fm == '4':
            continue
        # exclude vowels before /l/
        if m.fm == '5' and not m.cd == '39':
            continue
        # exclude vowels after /w, y/
        if m.ps == '9':
            continue
        # exclude vowels after obstruent + liquid clusters
        if m.ps == '8':
            continue
        # add measurements to means object
        if m.f1:
            means[m.cd].values[0].append(m.f1)
        if m.f2:
            means[m.cd].values[1].append(m.f2)
        if m.f3:
            means[m.cd].values[2].append(m.f3)

        # collect formant tracks
        means[m.cd].trackvalues.append(m.tracks)

    # calculate means and standard deviations
    for p in plotnik.PLOTNIKCODES:
        for i in range(3):
            means[p].n[i] = len(means[p].values[i])
                                # number of tokens for formant i
            mean, stdv = mean_stdv(means[p].values[i])
                                   # mean and standard deviation for formant i
            if mean:
                means[p].means[i] = round(mean, 0)
            if stdv:
                means[p].stdvs[i] = round(stdv, 0)

        # formant tracks
        for j in range(10):
            t_mean, t_stdv = mean_stdv([t[j] for t in means[p].trackvalues if t[j]])
            if t_mean and t_stdv != None:
                means[p].trackmeans.append((t_mean, t_stdv))
            else:  # can't leave empty values in the tracks
                means[p].trackmeans.append(('', ''))
    return means


def changeCase(word, case):
    """changes the case of output transcriptions to upper or lower case according to config settings"""

    if case == 'lower':
        w = word.lower()
    # assume 'upper' here
    else:
        w = word.upper()
    return w

def checkLocation(file):
    """checks whether a given file exists at a given location"""

    if not os.path.exists(file):
        print("ERROR:  Could not locate %s" % file)
        sys.exit()


def checkSpeechSoftware(speechSoftware):
    """checks that either Praat or ESPS is available as a speech analysis program"""

    if speechSoftware in ['ESPS', 'esps']:
        if os.name == 'nt':
            print("ERROR:  ESPS was specified as the speech analysis program, but this option is not yet compatible with Windows")
            sys.exit()
        if not programExists('formant'):
            print("ERROR:  ESPS was specified as the speech analysis program, but the command 'formant' is not in your path")
            sys.exit()
        else:
            return 'esps'
    elif speechSoftware in ['praat', 'Praat']:
        if not ((PRAATPATH and programExists(speechSoftware, PRAATPATH)) or (os.name == 'posix' and programExists(speechSoftware)) or (os.name == 'nt' and programExists('praatcon.exe'))):
            print("ERROR: Praat was specified as the speech analysis program, but the command 'praat' ('praatcon' for Windows) is not in your path")
            sys.exit()
        else:
            return speechSoftware
    else:
        print("ERROR: unsupported speech analysis software %s" % speechSoftware)
        sys.exit()


def checkTextGridFile(tgFile):
    """checks whether a TextGrid file exists and has the correct file format"""

    checkLocation(tgFile)
    lines = open(tgFile, 'r').readlines()
    if 'File type = "' not in lines[0]:
        print("ERROR:  %s does not appear to be a Praat TextGrid file (the string 'File type=' does not appear in the first line.)" % tgFile)
        sys.exit()


def checkTiers(tg, mfa):
    """performs a check on the correct tier structure of a TextGrid"""

    # odd tiers must be phone tiers; even tiers word tiers (but vice versa in terms of indices!)
    # last tier can (optionally) be style tier
    if mfa:
        phone_tier = lambda x: 2 * x + 1
        word_tier = lambda x: 2 * x
    else:
        phone_tier = lambda x: 2 * x
        word_tier = lambda x: 2 * x + 1
    speakers = []
    ns, style = divmod(len(tg), 2)
                       # "ns":  number of speakers (well, "noise" is not a speaker...)
    # style tier
    if style and tg[-1].name().strip().upper() not in ["STYLE", "FOCUS"]:
        sys.exit("ERROR!  Odd number of tiers in TextGrid, but last tier is not style tier.")
    else:
        # to make this compatible with output from the FA online interface
        # (where there are just two tiers)
        if ns == 1:  # len(tg) == 2:
            return speakers
        for i in range(ns):
            # even (in terms of indices) tiers must be phone tiers
            if not "PHONE" in tg[phone_tier(i)].name().split(' - ')[1].strip().upper():
                print("ERROR!  Tier %i should be phone tier but isn't." % phone_tier(i))
                sys.exit()
            # odd (in terms of indices) tiers must be word tiers
            elif not "WORD" in tg[word_tier(i)].name().split(' - ')[1].strip().upper():
                print("ERROR!  Tier %i should be word tier but isn't." % word_tier(i))
                sys.exit()
            # speaker name must be the same for phone and word tier
            elif tg[phone_tier(i)].name().split(' - ')[0].strip().upper() != tg[word_tier(i)].name().split(' - ')[0].strip().upper():
                print("ERROR!  Speaker name does not match for tiers %i and %i." % (phone_tier(i), word_tier(i)))
                sys.exit()
            else:
                # add speaker name to list of speakers
                speakers.append(tg[phone_tier(i)].name().split(' - ')[0].strip())

    if len(speakers) == 0:
        sys.exit("ERROR!  No speakers in TextGrid?!")
    else:
        return speakers


def checkWavFile(wavFile):
    """checks whether a given sound file exists at a given location"""

    checkLocation(wavFile)


def convertTimes(times, offset):
    """adds a specified offset to all time stamps"""

    convertedTimes = [t + offset for t in times]

    return convertedTimes


def detectMonophthong(formants, measurementPoint, index):
    """checks whether the formant tracks indicate a monophthong {m}, or a weak/shortented glide {s}"""

    # classify as a monophthong, weak/shortened glide or diphthong according to range of movement of F2:
    # if maximum F2 after point of measurement is less than 100 Hz above F2 at
    # point of measurement:  -> monophthong
    F2atPOM = formants[index][1]
    maximumF2AfterPOM = max([
                            formants[j][1] for j in range(index, len(formants)) if len(formants[j]) > 1])
    F2Movement = round(maximumF2AfterPOM - F2atPOM, 3)
    if F2Movement <= 100:
        glide = 'm'
    # if maximum F2 after point of measurement is between 100-300 Hz above F2
    # at point of measurement:  -> weak/shortened glide
    elif 100 < F2Movement <= 300:
        glide = 's'
    # if maximum F2 after point of measurement is more than 300 Hz above F2 at
    # point of measurement:  -> diphthong
    else:
        glide = ''

    return glide


def extractPortion(wavFile, vowelWavFile, beg, end, soundEditor):
    """extracts a single vowel (or any other part) from the main sound file"""

    if soundEditor == 'sox':  # this is the default setting, since it's faster
        # force output format because there have been issues with some sound
        # files where Praat could not read the extracted portion
        os.system(os.path.join(SOXPATH, 'sox') + ' ' + wavFile + ' -t wavpcm ' +
                  os.path.join(SCRIPTS_HOME, vowelWavFile) + ' trim ' + str(beg) + ' ' + str(end - beg))
    elif soundEditor == 'praat':
        os.system(os.path.join(PRAATPATH, PRAATNAME) + ' ' + SCRIPTS_HOME + '/extractSegment.praat ' +
                  os.path.join(os.path.pardir, wavFile) + ' ' + vowelWavFile + ' ' + str(beg) + ' ' + str(end))
    else:
        pass


def faav(phone, formants, times, intensity):
    """returns the time of measurement according to the FAAV guidelines"""

    # get intensity cutoffs for all vowels not measured one third into the
    # vowel
    if (phone.label[:-1] in ["AY", "EY", "OW", "AW"]) or (phone.label[:-1] == "UW" and phone.cd == "73"):
        # get intensity cutoff at 10% below maximum intensity
        beg_cutoff, end_cutoff = getIntensityCutoff(intensity.intensities(), intensity.times())
        # make sure we do have an intensity contour (i.e. several measurement point, and not just one)
        # if there is only one measurement point in the intensity object, the cutoffs will be identical
        # in that case, reset the cutoffs to include the whole vowel
        if beg_cutoff == end_cutoff:
            beg_cutoff = times[0]
            end_cutoff = times[-1]
        # modify cutoffs to make sure we are measuring in the first half of the
        # vowel
        beg_cutoff, end_cutoff = modifyIntensityCutoff(beg_cutoff, end_cutoff, phone, intensity.intensities(), intensity.times())

        # measure "AY" and "EY" at F1 maximum
        # (NOTE:  While "AY" receives extra padding at the beginning to possible go before the segment boundary in the search for an F1 maximum, "EY" does not)
        if phone.label[:-1] in ["AY", "EY"]:
            measurementPoint = getTimeOfF1Maximum(formants, times, beg_cutoff, end_cutoff)
        # measure Tuw at the beginning of the segment
        elif phone.label[:-1] == "UW" and phone.cd == "73":
            measurementPoint = max([phone.xmin, beg_cutoff])
        # measure "OW" and "AW" halfway between beginning of segment and F1
        # maximum
        elif phone.label[:-1] in ["OW", "AW"]:
            maxF1time = getTimeOfF1Maximum(formants, times, beg_cutoff, end_cutoff)
            if maxF1time > phone.xmin:
                measurementPoint = max([beg_cutoff, phone.xmin + (maxF1time - phone.xmin) / 2])
            else:
                measurementPoint = max([beg_cutoff, phone.xmin])
    # measure all other vowels at 1/3 of the way into the vowel's duration
    else:
        measurementPoint = phone.xmin + (phone.xmax - phone.xmin) / 3

    return measurementPoint


def getFormantTracks(poles, times, xmin, xmax):
    """returns formant tracks (values at 20%, 35%, 50%, 65% and 80% of the vowel duration)"""

    tracks = []
    # total duration of vowel
    dur = xmax - xmin
    # get measurement points for formant tracks (20%, 35%, 50%, 65% and 80%
    # into the vowel)
    measurement_times = [xmin + (0.2 * dur) + (0.15 * dur * i)
                         for i in range(5)]
    for t in measurement_times:
        index = getTimeIndex(t, times)
        try:
            F1 = poles[index][0]
            F2 = poles[index][1]
            tracks.append(F1)
            tracks.append(F2)
        except IndexError:
            # if we only have F1 but no matching F2, that measurement is probably not reliable enough
            # so append nothing for both of them
            tracks.append('')
            tracks.append('')

    return tracks


def getIntensityCutoff(intensities, times):
    """returns the beginning and end times for the 10%-below-maximum-intensity interval"""

    # get intensity cutoff and index of maximum intensity
    z_max = intensities.index(max(intensities))
    cutoff = 0.9 * max(intensities)
    # get left boundary
    z_left = 0
    for z in range(z_max, -1, -1):
        if intensities[z] < cutoff:
            z_left = z + 1
            break
    # get right boundary
    z_right = len(intensities) - 1
    for z in range(z_max, len(intensities)):
        if intensities[z] < cutoff:
            z_right = z - 1
            break

    beg_cutoff = times[z_left]
    end_cutoff = times[z_right]

    return beg_cutoff, end_cutoff


def getMeasurementPoint(phone, formants, times, intensity, measurementPointMethod):
    """returns the point of formant measurement, according to the measurement method selected"""

    if measurementPointMethod == 'third':
        # measure at 1/3 of the way into the vowel's duration
        measurementPoint = phone.xmin + (phone.xmax - phone.xmin) / 3
    elif measurementPointMethod == 'fourth':
        # measure at 1/4 of the way into the vowel's duration
        measurementPoint = phone.xmin + (phone.xmax - phone.xmin) / 4
    elif measurementPointMethod == 'mid':
        # measure at 1/2 of the way into the vowel's duration
        measurementPoint = phone.xmin + (phone.xmax - phone.xmin) / 2
    elif measurementPointMethod == 'lennig':
        # measure according to Lennig (1978)
        transition = getTransitionLength(phone.xmin, phone.xmax)
        # remove vowel transitions
        trimmedFormants, trimmedTimes = trimFormants(formants, times, phone.xmin + transition, phone.xmax - transition)
        measurementPoint = lennig(trimmedFormants, trimmedTimes)
    elif measurementPointMethod == 'anae':
        # measure according to the ANAE (2006) guidelines
        transition = getTransitionLength(phone.xmin, phone.xmax)
        # remove vowel transitions
        trimmedFormants, trimmedTimes = trimFormants(formants, times, phone.xmin + transition, phone.xmax - transition)
        measurementPoint = anae(phone.label, trimmedFormants, trimmedTimes)
    elif measurementPointMethod == 'faav':
        measurementPoint = faav(phone, formants, times, intensity)
    elif measurementPointMethod == 'maxint':
        measurementPoint = maximumIntensity(intensity.intensities(), intensity.times())
    else:
        print("ERROR: Unsupported measurement point selection method %s" % measurementPointMethod)
        print(__doc__)

    return measurementPoint


def getNumVowels(word):
    """returns the number of vowels in a word"""

    n = 0
    for p in word.phones:
        if isVowel(p.label):
            n += 1

    return n


def getPadding(phone, windowSize, maxTime):
    """checks that the padding for the analysis window does not exceed file boundaries; adjusts padding accordingly"""

    # if the phone is at the beginning (or end) of the sound file, we need to make sure that the added window will not
    # extend past the beginning (or end) of the file, since this will mess up extractPortion();
    # if it does, truncate the added window to the available space

    # check padding at beginning of vowel
    if phone.xmin - windowSize < 0:
        padBeg = phone.xmin
    # extend left padding for AY
    elif phone.label[:-1] == "AY":
        if phone.xmin - 2 * windowSize < 0:
            padBeg = phone.xmin
        else:
            padBeg = 2 * windowSize
    else:
        padBeg = windowSize
    # check padding at end of vowel
    if phone.xmax + windowSize > maxTime:
        padEnd = maxTime - phone.xmax
    else:
        padEnd = windowSize

    return (padBeg, padEnd)


def getSoundEditor():
    """checks whether SoX or Praat are available as sound editors"""

    # use sox for manipulating the files if we have it, since it's faster
    if (SOXPATH and programExists('sox', SOXPATH)) or (os.name == 'posix' and programExists('sox')) or (os.name == 'nt' and programExists('sox.exe')):
        soundEditor = 'sox'
    elif (PRAATPATH and programExists('praat', PRAATPATH)) or (os.name == 'posix' and programExists('praat')) or (os.name == 'nt' and programExists('praatcon.exe')):
        soundEditor = 'praat'
    else:
        print("ERROR:  neither 'praat' ('praatcon' for Windows) nor 'sox' can be found in your path")
        print("One of these two programs must be available for processing the audio file")
        sys.exit()

    return soundEditor


def getSpeakerBackground(speakername, speakernum):
    """prompts the user to enter background information for a given speaker"""

    speaker = Speaker()
    print("Please enter background information for speaker %s:" % speakername)
    print("(Press [return] if correct; if not, simply enter new data (do not use [delete]).)")
    speaker.name = input("Name:\t\t\t%s\t" % speakername.strip())
    if not speaker.name:
        speaker.name = speakername.strip()
    try:
        speaker.first_name = input("First name:\t\t%s\t" % speaker.name.strip().split()[0])
        if not speaker.first_name:
            speaker.first_name = speaker.name.strip().split()[0]
        # some speakers' last names are not known!
        try:
            # NOTE:  only initial letter of speaker's last name is
            # automatically taken over from tier name
            speaker.last_name = input("Last name:\t\t%s\t" % speaker.name.strip().split()[1][0])
            if not speaker.last_name:
                speaker.last_name = speaker.name.strip().split()[1][0]
        except IndexError:
            speaker.last_name = input("Last name:\t\t")
    except:
        speaker.first_name = ''
        speaker.last_name = ''
    speaker.sex = input("Sex:\t\t\t")
    # check that speaker sex is defined - this is required for the Mahalanobis
    # method!
    if formantPredictionMethod == "mahalanobis":
        if not speaker.sex:
            print("ERROR!  Speaker sex must be defined for the 'mahalanobis' formantPredictionMethod!")
            sys.exit()
    speaker.age = input("Age:\t\t\t")
##    speaker.city = input("City:\t\tPhiladelphia")
# if not speaker.city:
##        speaker.city = "Philadelphia"
##    speaker.state = input("State:\t\tPA")
# if not speaker.state:
##        speaker.state = "PA"
    speaker.ethnicity = input("Ethnicity:\t\t")
    speaker.location = input("Location:\t\t")
    speaker.year = input("Year of recording:\t")
    speaker.years_of_schooling = input("Years of schooling:\t")
    speaker.tiernum = speakernum * 2  
    # tiernum points to first tier for given speaker
    return speaker


def getTimeIndex(t, times):
    """gets the index of the nearest time value from an ordered list of times"""

    # the two following cases can happen if a short vowel is at the beginning
    # or end of a file
    if t < times[0]:
        # print "WARNING:  measurement point %f is less than earliest time stamp %f for formant measurements, selecting earliest point as measurement" % (t, times[0])
        # return the index of the first measurement
        return 0

    if t > times[-1]:
        # print "WARNING:  measurement point %f is less than latest time stamp %f for formant measurements, selecting latest point as measurement" % (t, times[-1])
        # return the index of the last measurement
        return len(times) - 1

    prev_time = 0.0
    for i in range(len(times)):
        if t > times[i]:
            prev_time = times[i]
            continue
        else:
            # determine nearest index
            if abs(t - prev_time) > abs(t - times[i]):
                return i
            else:
                return i - 1


def getTimeOfF1Maximum(formants, times, beg_cutoff, end_cutoff):
    """returns the time at which F1 reaches it maximum (within the cutoff limits)"""

    # get search interval for F1 maximum
    trimmedFormants, trimmedTimes = trimFormants(formants, times, beg_cutoff, end_cutoff)
    # get F1 maximum
    F1 = [f[0] if f else 0 for f in trimmedFormants]
        # 'else' for those weird cases where there is a hole in the formant tracks...
    i = F1.index(max(F1))
    measurementPoint = trimmedTimes[i]

    return measurementPoint


def getTransitionLength(minimum, maximum):
    """sets the transition time to the surrounding consonants to 20msec; if the vowel is shorter than 40msec, to zero"""

    # needed to remove transitions for Lennig and ANAE measurement methods
    if round(maximum - minimum, 3) <= 0.04:
        transition = 0
    else:
        transition = 0.02

    return transition


def getVowelMeasurement(vowelFileStem, p, w, speechSoftware, formantPredictionMethod, measurementPointMethod, nFormants, maxFormant, windowSize, preEmphasis, padBeg, padEnd, speaker):
    """makes a vowel measurement"""

    vowelWavFile = vowelFileStem + '.wav'

    # get necessary files (LPC or formant)
    # via ESPS:  ## NOTE:  I haven't checked the path issues for the ESPS
    # option yet...
    if speechSoftware == 'esps':
        esps.runFormant(vowelWavFile)
        if formantPredictionMethod == 'mahalanobis':
            lpc = esps.LPC()
            lpc.read(vowelFileStem + '.pole')
        else:
            fmt = esps.Formant()
            fmt.read(vowelFileStem + '.pole', vowelFileStem + '.fb')
        # clean up the temporary files we created for this vowel
        esps.rmFormantFiles(vowelFileStem)
    # via Praat:  ## NOTE:  all temp files are in the "/bin" directory!
    else:   # assume praat here
        if formantPredictionMethod == 'mahalanobis':
            # get measurements for nFormants = 3, 4, 5, 6
            LPCs = []
            nFormants = 3
            while nFormants <= 6:
                os.system(os.path.join(PRAATPATH, PRAATNAME) + ' ' + os.path.join(SCRIPTS_HOME, 'extractFormants.praat') + ' ' +
                          vowelWavFile + ' ' + str(nFormants) + ' ' + str(maxFormant) + ' ' ' ' + str(windowSize) + ' ' + str(preEmphasis) + ' burg')
                lpc = praat.Formant()
                lpc.read(os.path.join(SCRIPTS_HOME, vowelFileStem + '.Formant'))
                LPCs.append(lpc)
                nFormants += 1
        else:
            os.system(os.path.join(PRAATPATH, PRAATNAME) + ' ' + os.path.join(SCRIPTS_HOME, 'extractFormants.praat') + ' ' +
                      vowelWavFile + ' ' + str(nFormants) + ' ' + str(maxFormant) + ' ' + str(windowSize) + ' ' + str(preEmphasis) + ' burg')
            fmt = praat.Formant()
            fmt.read(os.path.join(SCRIPTS_HOME, vowelFileStem + '.Formant'))
        os.remove(os.path.join(SCRIPTS_HOME, vowelFileStem + '.Formant'))
        # get Intensity object for intensity cutoff
        # (only for those vowels where we need it)
        if (p.label[:-1] in ["AY", "EY", "OW", "AW"]) or (p.label[:-1] == "UW" and p.cd == "73"):
            os.system(os.path.join(PRAATPATH, PRAATNAME) + ' ' + os.path.join(SCRIPTS_HOME, 'getIntensity.praat') + ' ' + vowelWavFile)
            intensity = praat.Intensity()
            intensity.read(os.path.join(SCRIPTS_HOME, vowelFileStem + '.Intensity'))
            os.remove(os.path.join(SCRIPTS_HOME, vowelFileStem + '.Intensity'))
            intensity.change_offset(p.xmin - padBeg)
        else:
            intensity = praat.Intensity()
    # get measurement according to formant prediction method
    # Mahalanobis:
    if formantPredictionMethod == 'mahalanobis':
        convertedTimes = []
        poles = []
        bandwidths = []
        for lpc in LPCs:
            convertedTimes.append(convertTimes(lpc.times(), p.xmin - padBeg))
                                  # add offset to all time stamps from Formant
                                  # file
            poles.append(lpc.formants())
            bandwidths.append(lpc.bandwidths())
        vm = measureVowel(p, w, poles, bandwidths, convertedTimes, intensity, measurementPointMethod,
            formantPredictionMethod, padBeg, padEnd, means, covs)
    # default:
    else:   # assume 'default' here
        convertedTimes = [convertTimes(fmt.times(), p.xmin - padBeg)]
        formants = [fmt.formants()]
        bandwidths = [fmt.bandwidths()]
        vm = measureVowel(p, w, formants, bandwidths, convertedTimes, intensity, measurementPointMethod,
            formantPredictionMethod, padBeg, padEnd, '', '')

    os.remove(os.path.join(SCRIPTS_HOME, vowelWavFile))
    return vm


def getWordsAndPhones(tg, phoneset, speaker, vowelSystem, mfa):
    """takes a Praat TextGrid file and returns a list of the words in the file,
    along with their associated phones, and Plotnik codes for the vowels"""

    if mfa:
        phone_tier = lambda x: 2 * x + 1
        word_tier = lambda x: 2 * x
    else:
        phone_tier = lambda x: 2 * x
        word_tier = lambda x: 2 * x + 1
                     
    phone_midpoints = [p.xmin() + 0.5 * (p.xmax() - p.xmin()) \
                       for p in tg[phone_tier(int(speaker.tiernum/2))]]

    words = []
    # iterate along word tier for given speaker
    for w in tg[int(word_tier(int(speaker.tiernum/2)))]:  # for each interval...
        word = Word()
        word.transcription = w.mark()
        word.xmin = w.xmin()
        word.xmax = w.xmax()
        word.phones = []

        # get a slice of the phone tier which minimally includes phones
        # that are at least halfway contained in this word at each margin
        left = bisect_left(phone_midpoints, word.xmin)
        right = bisect_left(phone_midpoints, word.xmax)

        for p in tg[phone_tier(int(speaker.tiernum/2))][left:right]:

            phone = Phone()
            phone.label = p.mark().upper()
            phone.xmin = p.xmin()
            phone.xmax = p.xmax()
            word.phones.append(phone)
            # count initial number of vowels here! (because uncertain
            # transcriptions are discarded on a by-word basis)
            if phone.label and isVowel(phone.label):
                global count_vowels
                count_vowels += 1

        words.append(word)

    # add Plotnik-style codes for the preceding and following segments for all
    # vowels
    words = addPlotnikCodes(words, phoneset, speaker, vowelSystem)

    # add style codes, if applicable
    if len(tg) % 2:
        words = addStyleCodes(words, tg)

    # add overlap coding for phones
    words = addOverlaps(words, tg, speaker)

    return words


def hasPrimaryStress(label):
    """checks whether a vowel has primary stress"""

    if label[-1] == '1':  # NOTE:  this assumes that there are no empty intervals on the phone tier!
        return True
    else:
        return False


def isVowel(label):
    """checks whether a phone is a vowel"""

    # use the vowel inventory!
    if re.findall(r'^([A-Z]{2,2})\d?$', label.upper()) and re.findall(r'^([A-Z]{2,2})\d?$', label.upper())[0] in VOWELS:
        return True
    else:
        return False


def lennig(formants, times):
    """returns time of measurement according to Lennig's (1987) algorithm"""

    # initialize this to a number that will be larger than any of the change
    # coefficients
    prev = 1000000
    min_i = -1
    for i in range(1, len(formants) - 1):
        c = (abs(formants[i][0] - formants[i - 1][0]) + abs(formants[i][0] - formants[i + 1][0])) / \
            formants[i][0] + (abs(formants[i][1] - formants[i - 1][1]) + abs(formants[i][1] - formants[i + 1][1])) / formants[i][1]
        if c < prev:
            min_i = i
            prev = c
    measurementPoint = times[i]

    return measurementPoint


def loadCovs(inFile):
    """reads covariance matrix of training data set from file"""

    covs = {}
    for line in open(inFile, 'rU').readlines():
        vowel = line.strip().split('\t')[0]
        values = np.array([float(x) for x in line.strip().split('\t')[1:]])
        covs[vowel] = np.linalg.inv(np.reshape(values, (4, -1)))

    return covs


def loadMeans(inFile):
    """reads formant means of training data set from file"""

    means = {}
    for line in open(inFile, 'rU').readlines():
        vowel = line.strip().split('\t')[0]
        means[vowel] = np.array([float(x)
                                for x in line.strip().split('\t')[1:]])

    return means


def markTime(index1, index2=''):
    """generates a time stamp entry in global list logtimes[]"""

    real_time = time.time()
    logtimes.append((index1, real_time, index2))


def maximumIntensity(intensities, times):
    """returns the time of the intensity maximum"""

    i = intensities.index(max(intensities))
    measurementPoint = times[i]

    return measurementPoint


def mean_stdv(valuelist):
    """returns the arithmetic mean and sample standard deviation (N-1 in the denominator) of a list of values"""

    np_valuelist = np.array(valuelist,dtype=np.float64)
    if len(np_valuelist) > 0:
        if len(np_valuelist) == 1:
            mean = valuelist[0]
            stdv = 0
        else:
            mean = np.nanmean(np_valuelist)
            stdv = np.nanstd(np_valuelist, ddof=1)

    else:  # empty list
        mean = None
        stdv = None

    return mean, stdv


def measureVowel(phone, word, poles, bandwidths, times, intensity, measurementPointMethod, formantPredictionMethod, padBeg, padEnd, means, covs):
    """returns vowel measurement (formants, bandwidths, labels, Plotnik codes)"""

    # smooth formant tracks and bandwidths, if desired
    if nSmoothing:
        # check that smoothing is possible for the value of nSmoothing and the length of the vowel
        # (e.g. impossible to do a 25ms-window smoothing (default) on a 24ms vowel)
        # (second condition is for methods that add a 20 ms transition at the beginning of the vowel)
        if 2 * nSmoothing + 1 > len(times[0]):
            print("ERROR! Vowel %s in word %s is too short to be measured with selected value for smoothing parameter." % (phone.label, word.transcription))
            return None
        else:
            poles = [smoothTracks(p, nSmoothing) for p in poles]
            bandwidths = [smoothTracks(b, nSmoothing) for b in bandwidths]
            times = [t[nSmoothing:-nSmoothing] for t in times]

    if formantPredictionMethod == 'mahalanobis':
        selectedpoles = []
        selectedbandwidths = []
        measurementPoints = []
        all_tracks = []
        # predict F1 and F2 based on the LPC values at this point in time
        for j in range(4):
            # get point of measurement and corresponding index (closest to point of measurement) according to method specified in config file
            # NOTE:  Point of measurement and time index will be the same for "third", "mid", "fourth" methods for all values of nFormants
            # For "lennig", "anae" and "faav", which depend on the shape of the
            # formant tracks, different results will be obtained for different
            # nFormants settings.
            measurementPoint = getMeasurementPoint(phone, poles[j], times[j], intensity, measurementPointMethod)
            i = getTimeIndex(measurementPoint, times[j])
            measurementPoints.append((measurementPoint, i))
            selectedpoles.append(poles[j][i])
            selectedbandwidths.append(bandwidths[j][i])
            all_tracks.append(getFormantTracks(poles[j], times[j], phone.xmin-padBeg, phone.xmax+padEnd))

        f1, f2, f3, b1, b2, b3, winnerIndex = predictF1F2(phone, selectedpoles, selectedbandwidths, means, covs)
        # check that we actually do have a measurement (this may not be the
        # case for gaps in the wave form)
        if not f1 and not f2 and not f3 and not b1 and not b2 and not b3:
            return None
        measurementPoint = measurementPoints[winnerIndex][0]
        # get five sample points of selected formant tracks
        winner_poles = poles[winnerIndex]
        winner_bandwidths = bandwidths[winnerIndex]
        tracks = all_tracks[winnerIndex]

    else:  # formantPredictionMethod == 'default'
        measurementPoint = getMeasurementPoint(phone, poles[0], times[0], intensity, measurementPointMethod)
        i = getTimeIndex(measurementPoint, times[0])
        # (changed this so that "poles"/"bandwidths" only reflects measurements made at measurement point -
        # same as for Mahalanobis distance method)
        selectedpoles = poles[0][i]
        selectedbandwidths = bandwidths[0][i]
        f1 = selectedpoles[0]
        if len(selectedpoles) > 1:
            f2 = selectedpoles[1]
        else:
            f2 = ''
        if len(selectedpoles) > 2:
            f3 = selectedpoles[2]
        else:
            f3 = ''
        b1 = selectedbandwidths[0]
        if len(selectedpoles) > 1:
            b2 = selectedbandwidths[1]
        else:
            b2 = ''
        if len(selectedpoles) > 2:
            b3 = selectedbandwidths[2]
        else:
            b3 = ''
        # get five sample points of formant tracks
        tracks = getFormantTracks(poles[0], times[0], phone.xmin, phone.xmax)
        all_tracks = []
        winner_poles = poles[0]
        winner_bandwidths = bandwidths[0]

    # put everything together into VowelMeasurement object
    vm = VowelMeasurement()
    vm.phone = phone.label[
        :-1]  # phone label (Arpabet coding, excluding stress)
    vm.stress = phone.label[-1]  # stress level
    vm.style = word.style  # stylistic coding
    vm.word = word.transcription  # corresponding word
    vm.f1 = round(f1, 1)  # formants
    if f2 != '':
        vm.f2 = round(f2, 1)
    if f3 != '':
        vm.f3 = round(f3, 1)
    vm.b1 = round(b1, 1)  # bandwidths
    if b2 != '':
        vm.b2 = round(b2, 1)
    if b3 != '':
        vm.b3 = round(b3, 1)
    vm.t = round(measurementPoint, 3)  # measurement time (rounded to msec)
    vm.code = phone.code  # Plotnik vowel code (whole code?)
    vm.cd = phone.cd  # Plotnik code for vowel class
    vm.fm = phone.fm  # Plotnik code for manner of following segment
    vm.fp = phone.fp  # Plotnik code for place of following segment
    vm.fv = phone.fv  # Plotnik code for voicing of following segment
    vm.ps = phone.ps  # Plotnik code for preceding segment
    vm.fs = phone.fs  # Plotnik code for following sequences
    vm.beg = round(phone.xmin, 3)  # beginning of vowel (rounded to msec)
    vm.end = round(phone.xmax, 3)  # end of vowel (rounded to msec)
    vm.dur = round(phone.xmax - phone.xmin, 3)
                   # duration of vowel (rounded to msec)
    vm.poles = selectedpoles  # original poles returned by LPC analysis
    vm.bandwidths = selectedbandwidths  # original bandwidths returned by LPC analysis
    vm.times = times

    if formantPredictionMethod == 'mahalanobis':
        vm.nFormants = winnerIndex + \
            3  # actual formant settings used in the analysis
        if phone.label[:-1] == "AY":
            vm.glide = detectMonophthong(poles[winnerIndex], measurementPoints[
                                         winnerIndex][0], measurementPoints[winnerIndex][1])
    vm.tracks = tracks  # F1 and F2 measurements at 20%, 35%, 50%, 65% and 80% of the vowel duration
    vm.all_tracks = all_tracks  # list of formant tracks for all possible formant settings (needed for remeasurement)
    vm.winner_bandwidths = winner_bandwidths
    vm.winner_poles = winner_poles
    vm.all_poles = poles
    vm.all_bandwidths = bandwidths
    vm.times = times

    return vm


def modifyIntensityCutoff(beg_cutoff, end_cutoff, phone, intensities, times):
    """modifies initial intensity cutoff to ensure measurement takes place in the first half of the vowel"""

    midpoint = phone.xmin + (phone.xmax - phone.xmin) / 2

    # no matter where the intensity contour drops, we want to measure in the first half of the vowel
    # (second condition is to ensure that there are still formants in the selected frames -
    # this might not be the case e.g. with a long segment of
    # glottalization/silence included at the beginning of the vowel)
    if end_cutoff > midpoint and midpoint > beg_cutoff:
        end_cutoff = midpoint
    # exclude cases where the intensity maximum is at the end of the segment
    # (because of a following vowel)
    if beg_cutoff > midpoint:
        # in this case, look for new intensity maximum and cutoffs in the first
        # half of the vowel
        trimmedIntensities, trimmedTimes = trimFormants(intensities, times, phone.xmin, midpoint)
        beg_cutoff, end_cutoff = getIntensityCutoff(trimmedIntensities, trimmedTimes)

    return beg_cutoff, end_cutoff


def normalize(measurements, m_means):
    """normalized measurements according to the Lobanov method"""

    values = [[], [], []]
    grand_means = [0, 0, 0]
    grand_stdvs = [0, 0, 0]
    # collect measurement values for each formant
    for m in measurements:
        if m.f1:
            values[0].append(m.f1)
        if m.f2:
            values[1].append(m.f2)
        if m.f3:
            values[2].append(m.f3)
    # get overall means and standard deviations for each formant
    for i in range(3):
        grand_means[i], grand_stdvs[i] = mean_stdv(values[i])

    # normalize individual measurements
    for m in measurements:
        try:
            m.norm_f1 = round(650 + 150 * (lobanov(m.f1, grand_means[0], grand_stdvs[0])), 0)
        except TypeError:
            m.norm_f1 = ''
        try:
            m.norm_f2 = round(1700 + 420 * (lobanov(m.f2, grand_means[1], grand_stdvs[1])), 0)
        except TypeError:
            m.norm_f2 = ''
# try:
##            m.norm_f3 = round(lobanov(m.f3, grand_means[2], grand_stdvs[2]), 0)
# except TypeError:
##            m.norm_f3 = None
        m.norm_f3 = ''  # don't normalize F3 right now - we don't have any reasonable scaling factors

        # normalize formant tracks for individual measurements
        for i in range(5):
            if m.tracks[2 * i] and m.tracks[2 * i + 1]:
                m.norm_tracks.append(round(650 + 150 * (lobanov(m.tracks[2 * i], grand_means[0], grand_stdvs[0])), 0))  # F1
                m.norm_tracks.append(round(1700 + 420 * (lobanov(m.tracks[2 * i + 1], grand_means[1], grand_stdvs[1])), 0))  # F2
            else:
                m.norm_tracks.append('')  # F1
                m.norm_tracks.append('')  # F2

    # normalize the means and standard deviations for F1 and F2
    for p in plotnik.PLOTNIKCODES:
        # F1 mean
        try:
            m_means[p].norm_means[0] = round(650 + 150 * (lobanov(m_means[p].means[0], grand_means[0], grand_stdvs[0])), 0)
        except TypeError:
# print "No F1 normalized mean for vowel class %s:  value = %s, mean = %s,
# stdv = %s." % (p, m_means[p].means[0], grand_means[0], grand_stdvs[0])
            m_means[p].norm_means[0] = ''
        # F1 standard deviation
        try:
            m_means[p].norm_stdvs[0] = round(150 * (m_means[p].stdvs[0] / grand_stdvs[0]), 0)
        except TypeError:
# print "No F1 normalized standard deviation for vowel class %s:  value =
# %s, stdv = %s." % (p, m_means[p].stdvs[0], grand_stdvs[0])
            m_means[p].norm_stdvs[0] = ''
        # F2 mean
        try:
            m_means[p].norm_means[1] = round(1700 + 420 * (lobanov(m_means[p].means[1], grand_means[1], grand_stdvs[1])), 0)
        except TypeError:
# print "No F2 normalized mean for vowel class %s:  value = %s, mean = %s,
# stdv = %s." % (p, m_means[p].means[1], grand_means[1], grand_stdvs[1])
            m_means[p].norm_means[1] = ''
        # F2 standard deviation
        try:
            m_means[p].norm_stdvs[1] = round(420 * (m_means[p].stdvs[1] / grand_stdvs[1]), 0)
        except TypeError:
# print "No F2 normalized standard deviation for vowel class %s:  value =
# %s, stdv = %s." % (p, m_means[p].stdvs[1], grand_stdvs[1])
            m_means[p].norm_stdvs[1] = ''

        # normalize mean formant tracks
        for i in range(5):
            try:
                m_means[p].trackmeans_norm.append((round(650 + 150 * (lobanov(m_means[
                        p].trackmeans[
                        2 * i][0], grand_means[0], grand_stdvs[0])), 0),
                     round(150 * (m_means[p].trackmeans[2 * i][1] / grand_stdvs[0]), 0)))  # mean and stdv for F1
            except TypeError:
                m_means[p].trackmeans_norm.append(('', ''))
            try:
                m_means[p].trackmeans_norm.append((round(1700 + 420 * (lobanov(m_means[
                        p].trackmeans[
                        2 * i + 1][0], grand_means[1], grand_stdvs[1])), 0),
                     round(420 * (m_means[p].trackmeans[2 * i + 1][1] / grand_stdvs[1]), 0)))
            except TypeError:
                m_means[p].trackmeans_norm.append(('', ''))

# print m_means[p]
# print "\n"

    return measurements, m_means


def lobanov(value, mean, stdv):
    """converts a value into its corresponding z-score"""

    if value and mean and stdv:
        return (value - mean) / stdv
    else:  # not enough tokens for normalization, or no mean to normalize
        return ''


def outputFormantSettings(measurements, speaker, outputFile):
    """summarizes the formant settings used for each vowel class in a separate file"""

    # initialize counting dictionary; use tuples (Plotnik code, nFormants) as
    # indices
    count = {}
    for code in plotnik.PLOTNIKCODES:
        for nf in range(3, 7):
            count[(str(code), nf)] = 0
    for vm in measurements:
        count[(str(vm.cd), int(vm.nFormants))] += 1

    # filename = name of the output file, but with extension "nFormants"
    outfilename = os.path.splitext(outputFile)[0] + ".nFormants"
    f = open(outfilename, 'w')
    f.write("Formant settings for %s:\n\n" % outputFile)
    f.write(', '.join([speaker.name, speaker.age, speaker.sex, speaker.city, speaker.state, speaker.year]))
    f.write('\n\n')
    f.write('\t'.join(['vowel', '3', '4', '5', '6']))
    f.write('\n')
    f.write('----------------------------------------\n')
    for code in plotnik.PLOTNIKCODES:
        f.write(code)
        for nf in range(3, 7):
            f.write('\t' + str(count[(str(code), nf)]))
        f.write('\n')
    f.close()


def outputMeasurements(outputFormat, measurements, m_means, speaker, outputFile, outputHeader, tracks):
    """writes measurements to file according to selected output format"""

    ## outputFormat = "text"
    if outputFormat in ['txt', 'text', 'both']:
        fw = open(os.path.splitext(outputFile)[0] + ".txt", 'w')
                  # explicitly generate different extensions for "both" option
        # print header, if applicable
        if outputHeader:
            # speaker information
            s_dict = speaker.__dict__
            s_keys = sorted(s_dict.keys())

            fw.write('\t'.join(s_keys))
            fw.write('\t')
            fw.write('\t'.join(['vowel', 'stress', 'pre_word', 'word', 'fol_word',
                                'F1', 'F2', 'F3',
                                'B1', 'B2', 'B3', 't', 'beg', 'end', 'dur',
                                'plt_vclass', 'ipa_vclass', 'plt_manner', 'plt_place',
                                'plt_voice', 'plt_preseg', 'plt_folseq', 'style',
                                'glide', 'pre_seg', 'fol_seg', 'context',
                                'vowel_index', 'pre_word_trans', 'word_trans',
                                'fol_word_trans', 'F1@20%', 'F2@20%',
                                'F1@35%','F2@35%', 'F1@50%', 'F2@50%',
                                'F1@65%','F2@65%', 'F1@80%', 'F2@80%']))
            if formantPredictionMethod == 'mahalanobis':
                fw.write('\t')
                fw.write('nFormants')
            if candidates:
                fw.write('\t')
                fw.write('\t'.join(['poles', 'bandwidths']))
            fw.write('\n')
        # individual measurements
        for vm in measurements:
            for speaker_attr in s_keys:
                fw.write(str(s_dict[speaker_attr]))
                fw.write('\t')
            fw.write('\t'.join([vm.phone, str(vm.stress), vm.pre_word, vm.word, vm.fol_word, str(vm.f1)]))
                     # vowel (ARPABET coding), stress, word, F1

            fw.write('\t')
            if vm.f2:
                fw.write(str(vm.f2))  # F2 (if present)

            fw.write('\t')
            if vm.f3:
                fw.write(str(vm.f3))  # F3 (if present)

            fw.write('\t')
            fw.write(str(vm.b1))  # B1

            fw.write('\t')
            if vm.b2:
                fw.write(str(vm.b2))  # B2

            fw.write('\t')
            if vm.b3:
                fw.write(str(vm.b3))  # B3 (if present)

            fw.write('\t')
            fw.write('\t'.join( [str(vm.t), str(vm.beg), str(vm.end),
                                 str(vm.dur),
                                 plotnik.plt_vowels(vm.cd),
                                 plotnik.plt_ipa(vm.cd),
                                 plotnik.plt_manner(vm.fm),
                                 plotnik.plt_place(vm.fp),
                                 plotnik.plt_voice(vm.fv),
                                 plotnik.plt_preseg(vm.ps),
                                 plotnik.plt_folseq(vm.fs), vm.style, vm.glide,
                                 vm.pre_seg,
                                 vm.fol_seg, vm.context, vm.p_index,
                                 vm.pre_word_trans, vm.word_trans,
                                 vm.fol_word_trans]))
            fw.write('\t')
                     # time of measurement, beginning and end of phone,
                     # duration, Plotnik environment codes, style coding, glide
                     # coding
            fw.write('\t'.join([str(round(t, 1)) if t else '' for t in vm.tracks]))  # formant tracks

            if vm.nFormants:
                fw.write('\t')
                fw.write(str(vm.nFormants))
                         # nFormants selected (if Mahalanobis method)
            if candidates:
                fw.write('\t')
                fw.write('\t'.join([','.join([str(p) for p in vm.poles]), ','.join([str(b) for b in vm.bandwidths])]))
                         # candidate poles and bandwidths (at point of
                         # measurement)
            fw.write('\n')
        fw.close()
        print("Vowel measurements output in .txt format to the file %s" % (os.path.splitext(outputFile)[0] + ".txt"))

        # normalized measurements
        fw = open(os.path.splitext(outputFile)[0] + "_norm.txt", 'w')
        # print header, if applicable
        if outputHeader:
            # speaker information
            fw.write(', '.join([speaker.name, speaker.age, speaker.sex, speaker.ethnicity, speaker.years_of_schooling, speaker.location, speaker.year]))
            fw.write('\n\n')
            # header
            fw.write('\t'.join(['vowel', 'stress', 'word', 'norm_F1', 'norm_F2', 't', 'beg', 'end', 'dur',
                           'cd', 'fm', 'fp', 'fv', 'ps', 'fs', 'style', 'glide',
                           'norm_F1@20%', 'norm_F2@20%', 'norm_F1@35%', 'norm_F2@35%', 'norm_F1@50%', 'norm_F2@50%',
                           'norm_F1@65%', 'norm_F2@65%', 'norm_F1@80%', 'norm_F2@80%']))
            if formantPredictionMethod == 'mahalanobis':
                fw.write('\t')
                fw.write('nFormants')
            fw.write('\n')
        # individual measurements
        for vm in measurements:
            fw.write('\t'.join([vm.phone, str(vm.stress), vm.word, str(vm.norm_f1), str(vm.norm_f2)]))
                     # vowel (ARPABET coding), stress, word, F1, F2
            fw.write('\t')
            fw.write('\t'.join([str(vm.t), str(vm.beg), str(vm.end), str(vm.dur), vm.cd, vm.fm, vm.fp, vm.fv, vm.ps, vm.fs, vm.style, vm.glide]))
            fw.write('\t')
                     # time of measurement, beginning and end of phone,
                     # duration, Plotnik environment codes, style coding, glide
                     # coding
            fw.write('\t'.join([str(round(t, 1)) if t else '' for t in vm.norm_tracks]))  # formant tracks
            fw.write('\t')
            if vm.nFormants:
                fw.write(str(vm.nFormants))
                         # nFormants selected (if Mahalanobis method)
                fw.write('\t')
            fw.write('\n')
        fw.close()
        print("Normalized vowel measurements output in .txt format to the file %s" % (os.path.splitext(outputFile)[0] + "_norm.txt"))

        if tracks:
            with open(os.path.splitext(outputFile)[0]+".tracks", 'w') as trackfile:
                trackwriter = csv.writer(trackfile, delimiter = "\t", )
                s_dict = speaker.__dict__
                s_keys = sorted(s_dict.keys())
                speaker_attrs = [s_dict[x] for x in s_keys]
                v_header = ['id', 'vowel', 'stress', 'pre_word', 'word', 'fol_word',
                                'F1_meas', 'F2_meas', 'F3_meas',
                                'F1', 'F2', 'F3',
                                'B1', 'B2', 'B3', 't', 't_meas', 'dur',
                                'plt_vclass', 'ipa_vclass', 'plt_manner', 'plt_place',
                                'plt_voice', 'plt_preseg', 'plt_folseq', 'style',
                                'glide', 'pre_seg', 'fol_seg', 'context',
                                'vowel_index', 'pre_word_trans', 'word_trans',
                                'fol_word_trans']

                trackwriter.writerow(s_keys + v_header)

                for nmeas, vm in enumerate(measurements):
                    if len(vm.winner_poles[0]) < 2:
                        continue

                    vowel_info = [nmeas, vm.phone, vm.stress, vm.pre_word, vm.word, vm.fol_word, vm.f1, vm.f2]
                    context_info = [str(vm.t),
                                 str(vm.dur),
                                 plotnik.plt_vowels(vm.cd),
                                 plotnik.plt_ipa(vm.cd),
                                 plotnik.plt_manner(vm.fm),
                                 plotnik.plt_place(vm.fp),
                                 plotnik.plt_voice(vm.fv),
                                 plotnik.plt_preseg(vm.ps),
                                 plotnik.plt_folseq(vm.fs), vm.style, vm.glide,
                                 vm.pre_seg,
                                 vm.fol_seg, vm.context, vm.p_index,
                                 vm.pre_word_trans, vm.word_trans,
                                 vm.fol_word_trans]
                    if vm.f3:
                        vowel_info = vowel_info + [vm.f3]
                    else:
                        vowel_info = vowel_info + ['']
                    f1_tracks = [p[0] for p in vm.winner_poles]
                    f2_tracks = [p[1] if len(p) >= 2 else '' for p in vm.winner_poles]
                    f3_tracks = [p[2] if len(p) >= 3 else '' for p in vm.winner_poles]

                    b1_tracks = [b[0] if len(b) >= 1 else '' for b in vm.winner_bandwidths]
                    b2_tracks = [b[1] if len(b) >= 2 else '' for b in vm.winner_bandwidths]
                    b3_tracks = [b[2] if len(b) >= 3 else '' for b in vm.winner_bandwidths]
                    times = vm.times[0]

                    for f1, f2, f3, b1, b2, b3, t in zip(f1_tracks, f2_tracks, f3_tracks,
                                                         b1_tracks, b2_tracks, b3_tracks,
                                                         times):
                        trackwriter.writerow(speaker_attrs + vowel_info + [f1, f2, f3, b1, b2, b3, t] +
                                             context_info)






    ## outputFormat = "plotnik"
    if outputFormat in ['plotnik', 'Plotnik', 'plt', 'both']:
        plt = plotnik.PltFile()
        # transfer speaker information
        plt.first_name = speaker.first_name
        plt.last_name = speaker.last_name
        plt.age = speaker.age
        plt.sex = speaker.sex
        plt.city = speaker.city
        plt.state = speaker.state
        plt.ethnicity = speaker.ethnicity
        plt.years_of_schooling = speaker.years_of_schooling
        plt.location = speaker.location
        plt.year = speaker.year
        for vm in measurements:
            plt.measurements.append(vm)
        plt.N = len(plt.measurements)
        plt.means = m_means
        plotnik.outputPlotnikFile(plt, os.path.splitext(outputFile)[
                                  0] + ".plt")  # explicitly generate different extensions for "both" option
    if outputFormat not in ['plotnik', 'Plotnik', 'plt', 'txt', 'text', 'both']:
        print("ERROR: Unsupported output format %s" % outputFormat)
        print(__doc__)
        sys.exit(0)

    # write summary of formant settings to file
    if formantPredictionMethod == 'mahalanobis':
        outputFormantSettings(measurements, speaker, outputFile)

def parseStopWordsFile(f):
    """reads a file of stop words into a list"""

    # if removeStopWords = "T"
    # file specified by "--stopWords" option in command line input
    stopWords = open(f, 'r').read().splitlines()
    return stopWords


def predictF1F2(phone, selectedpoles, selectedbandwidths, means, covs):
    """returns F1 and F2 (and bandwidths) as determined by Mahalanobis distance to ANAE data"""

    # phone = vowel to be analyzed
    # poles =
    # bandwidths =
    # means =
    # covs =

    vowel = phone.cd  # Plotnik vowel code
    values = []
        # this list keeps track of all pairs of poles/bandwidths "tested"
    distances = []
        # this list keeps track of the corresponding value of the Mahalanobis distance
    # for all values of nFormants:
    if vowel in means:
        for poles, bandwidths in zip(selectedpoles, selectedbandwidths):
            # check that there are at least two formants in the selected frame
            if len(poles) >= 2:
                # nPoles = len(poles)     ## number of poles
                # check all possible combinations of F1, F2, F3:
                # for i in range(min([nPoles - 1, 2])):
                #    for j in range(i+1, min([nPoles, 3])):
                        i = 0
                        j = 1
                        # vector with current pole combination and associated
                        # bandwidths
                        x = np.array([poles[i], poles[j], math.log(bandwidths[i]), math.log(bandwidths[j])])
                        # calculate Mahalanobis distance between x and ANAE mean
                        dist = mahalanobis(x, means[vowel], covs[vowel])
                        # append poles and bandwidths to list of values
                        # (if F3 and bandwidth measurements exist, add to list of appended values)
                        if len(poles) > 2:
                            values.append(
                                [poles[i], poles[j], bandwidths[i], bandwidths[j], poles[2], bandwidths[2]])
                        else:
                            values.append([poles[i], poles[j], bandwidths[i], bandwidths[j], '', ''])
                        # append corresponding Mahalanobis distance to list of
                        # distances
                        distances.append(dist)
            # we need to append something to the distances and values lists so that the winnerIndex still corresponds with nFormants!
            # (this is for the case that the selected formant frame only contains F1 - empty string will not be selected as minimum distance)
            else:
                # if there are gaps in the formant tracks and the vowel duration is
                # short, the whole formant track may disappear during smoothing
                if len(poles) == 1 and len(bandwidths) == 1:
                    values.append([poles[0], '', bandwidths[0], '', '', ''])
                else:
                    values.append(['', '', '', '', '', ''])
                distances.append('')
        # get index for minimum Mahalanobis distance
        winnerIndex = distances.index(min([float(x) for x in distances if x != '']))
        # get corresponding F1, F2 and bandwidths values
        f1 = values[winnerIndex][0]
        f2 = values[winnerIndex][1]
        f3 = values[winnerIndex][4]
        # if there is a "gap" in the wave form at the point of measurement, the bandwidths returned will be empty,
        # and the following will cause an error...
        if values[winnerIndex][2]:
            b1 = values[winnerIndex][2]
        else:
            b1 = ''
        if values[winnerIndex][3]:
            b2 = values[winnerIndex][3]
        else:
            b2 = ''
        if values[winnerIndex][5]:
            b3 = values[winnerIndex][5]
        else:
            b3 = ''
        # return tuple of measurements
    else:
        winnerIndex = 2
        f1 = selectedpoles[2][0]
        f2 = selectedpoles[2][1]
        f3 = selectedpoles[2][2]
        if selectedbandwidths[2][0]:
            b1 = selectedbandwidths[2][0]
        else:
            b1 = ''
        if selectedbandwidths[2][1]:
            b2 = selectedbandwidths[2][1]
        else:
            b2 = ''
        if selectedbandwidths[2][2]:
            b3 = selectedbandwidths[2][2]
        else:
            b3 = ''

    return (f1, f2, f3, b1, b2, b3, winnerIndex)


def processInput(wavInput, tgInput, output):
    """for the "multipleFiles" option, processes the three files which contain lists of input filenames,
    one filename per line; returns list of filenames"""

    # remove the trailing newline character from each line of the file, and
    # store the filenames in a list
    wavFiles = open(wavInput, 'r').read().splitlines()
    tgFiles = open(tgInput, 'r').read().splitlines()
    outputFiles = open(output, 'r').read().splitlines()
    return (wavFiles, tgFiles, outputFiles)


def programExists(program, path=''):
    """checks whether a given command line program exists (path can be specified optionally)"""

    if not path:
        if os.name == 'posix':
            pathDirs = os.environ['PATH'].split(':')
        elif os.name == 'nt':
            pathDirs = os.environ['PATH'].split(';')
        else:
            print("ERROR: did not recognize OS type '%s'. Paths to 'praat' and 'sox' must be specified manually" % os.name)
            sys.exit()
        for p in pathDirs:
            if os.path.isfile(os.path.join(p, program)):
                return True
        return False
    else:  # path is specified
        return os.path.isfile(os.path.join(path, program))


def readSpeakerFile(speakerFile):
    """reads speaker background information from a speaker file"""

    speaker = Speaker()

    speaker_parser = argparse.ArgumentParser(description="parses a .speaker file",
                                     fromfile_prefix_chars="+")
    speaker_parser.add_argument("--name")
    speaker_parser.add_argument("--first_name")
    speaker_parser.add_argument("--last_name")
    speaker_parser.add_argument("--age")
    speaker_parser.add_argument("--sex",
        choices = ["m","M","male","MALE", "f","F","female","FEMALE"],
        required = True)
    speaker_parser.add_argument("--ethnicity")
    speaker_parser.add_argument("--years_of_schooling")
    speaker_parser.add_argument("--location")
    speaker_parser.add_argument("--city")
    speaker_parser.add_argument("--state")
    speaker_parser.add_argument("--year")
    speaker_parser.add_argument("--speakernum")
    speaker_parser.add_argument("--tiernum")
    speaker_parser.add_argument("--vowelSystem",
        choices = ['phila', 'Phila', 'PHILA', 'NorthAmerican', 'simplifiedARPABET'])

    speaker_opts = speaker_parser.parse_args(["+"+speakerFile])

    if speaker_opts.speakernum is None and speaker_opts.tiernum is None:
        print("Warning, analyzing first speaker by default.")
        setattr(speaker, "tiernum", 0)
    elif speaker_opts.tiernum:
        if speaker_opts.tiernum % 2 != 0:
            print("Warning, invalid tiernum. Try specifying --speakernum instead")
        else:
            setattr(speaker, "tiernum", speaker_opts.tiernum)
    elif speaker_opts.speakernum:
        setattr(speaker, "tiernum", (int(speaker_opts.speakernum) - 1) * 2)

    speaker_opts_dict = speaker_opts.__dict__
    speaker_opts_keys = [x for x in speaker_opts_dict.keys() if \
        x not in ["tiernum", "speakernum", "vowelSystem"] and \
        speaker_opts_dict[x] is not None]

    for attribute in speaker_opts_keys:
        value = speaker_opts_dict[attribute]

        # check that attribute for speaker exists
        if hasattr(speaker, attribute):
            setattr(speaker, attribute, value)
            # print "Added attribute %s with value %s to speaker object." %
            # (attribute, value)
        else:
            print("WARNING!  Speaker object has not attribute %s (value %s)!" % (attribute, value))
            # set full name of speaker
            speaker.name = speaker.first_name + ' ' + speaker.last_name

    if speaker_opts.vowelSystem:
        global vowelSystem
        vowelSystem = value




    return speaker

def setup_parser():
    parser = argparse.ArgumentParser(description="Takes as input a sound file and a Praat .TextGrid file (with word and phone tiers) and outputs automatically extracted F1 and F2 measurements for each vowel (either as a tab-delimited text file or as a Plotnik file).",
                                     usage='python %(prog)s [options] filename.wav filename.TextGrid outputFile [--stopWords ...]',
                                     fromfile_prefix_chars="+")
    parser.add_argument("--candidates", action="store_true",
                        help="Return all candidate measurements in output")
    parser.add_argument("--case", choices=["lower","upper"], default="upper",
                        help="Return word transcriptions in specified case.")
    parser.add_argument("--covariances", "-r",  default=pkg_resources.resource_filename('fave.extract', 'config/covs.txt'),
                        help="covariances, required for mahalanobis method")
    parser.add_argument("--formantPredictionMethod", choices = ["default","mahalanobis"], default = "mahalanobis",
                        help="Formant prediction method")
    parser.add_argument("--maxFormant", type=int, default=5000)
    parser.add_argument("--means", "-m",  default=pkg_resources.resource_filename('fave.extract', 'config/means.txt'),
                        help="mean values, required for mahalanobis method")
    parser.add_argument("--measurementPointMethod", choices = ['fourth', 'third', 'mid', 'lennig', 'anae', 'faav', 'maxint'],
                        default="faav", help = "Method for determining measurement point")
    parser.add_argument("--mfa", action="store_true", 
                        help = "Alignment is from the Montreal Forced Aligner")
    parser.add_argument("--minVowelDuration", type=float, default=0.05,
                        help = "Minimum duration in seconds, below which vowels won't be analyzed.")
    parser.add_argument("--multipleFiles", action="store_true",
                        help="Interpret positional arguments as files of listed .wav, .txt and output files.")
    parser.add_argument("--nFormants", type=int, default=5,
                        help="Specify the order of the LPC analysis to be conducted")
    parser.add_argument("--noOutputHeader", action="store_true",
                        help="Don't include output header in text output.")
    parser.add_argument("--nSmoothing", type=int, default=12,
                        help="Specifies the number of samples to be used for the smoothing of the formant tracks.")
    parser.add_argument("--onlyMeasureStressed", action="store_true")
    parser.add_argument("--outputFormat",   "-o",  choices = ['txt', 'text', 'plotnik', 'Plotnik', 'plt', 'both'], default="txt",
                        help = "Output format. Tab delimited file, plotnik file, or both.")
    parser.add_argument("--preEmphasis", type=float, default=50,
                        help="The cut-off value in Hz for the application of a 6 dB/octave low-pass filter.")
    parser.add_argument("--phoneset", "-p",  default = pkg_resources.resource_filename('fave.extract', 'config/cmu_phoneset.txt'))
    parser.add_argument("--pickle", action = "store_true",
                        help = "save vowel measurement information as a picklefile")
    parser.add_argument("--remeasurement", action="store_true",
                        help="Do a second pass is performed on the data, using the speaker's own system as the base of comparison for the Mahalanobis distance")
    parser.add_argument("--removeStopWords", action="store_true",
                        help="Don't measure vowels in stop words." )
    parser.add_argument("--speechSoftware", choices = ['praat', 'Praat', 'esps', 'ESPS'], default = "Praat",
                        help="The speech software program to be used for LPC analysis.")
    parser.add_argument("--speaker",  "-s",
                        help = "*.speaker file, if used")
    parser.add_argument("--stopWords", nargs="+", default=["AND", "BUT", "FOR", "HE", "HE'S", "HUH", "I", "I'LL", "I'M", "IS", "IT", "IT'S", "ITS", "MY", "OF", "OH",
                        "SHE", "SHE'S", "THAT", "THE", "THEM", "THEN", "THERE", "THEY", "THIS", "UH", "UM", "UP", "WAS", "WE", "WERE", "WHAT", "YOU"],
                        help = "Words to be excluded from measurement")
    parser.add_argument("--stopWordsFile",      "-t",
                        help = "file containing words to exclude from analysis")
    parser.add_argument("--tracks", action="store_true",
                        help = "Write full formant tracks.")
    parser.add_argument("--vowelSystem", choices = ['phila', 'Phila', 'PHILA', 'NorthAmerican', 'simplifiedARPABET'],
                        default="NorthAmerican",help="If set to Phila, a number of vowels will be reclassified to reflect the phonemic distinctions of the Philadelphia vowel system.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help = "verbose output. useful for debugging")
    parser.add_argument("--windowSize", type=float, default=0.025,
                        help="In sec, the size of the Gaussian window to be used for LPC analysis.")
    parser.add_argument("wavInput",
                        help = "*.wav audio file")
    parser.add_argument("tgInput",
                        help = "*.TextGrid alignment")
    parser.add_argument("output",
                        help="File stem for output")

    return(parser)

def smoothTracks(poles, s):
    """smoothes formant/bandwidth tracks by averaging over a window of 2s+1 samples"""

    # poles = list of (list of F1, F2, F3, ...) for each point in time
    # BUT number of formants in each frame may be different!
    maxNumFormants = max([len(p) for p in poles])
    new_poles = []
    for i in range(s, len(poles) - s):
        new_poles.append([])
    # smooth each formant track separately
    for n in range(maxNumFormants):
        for i in range(s, len(poles) - s):
            # start with values at point i; check that center point values are
            # defined
            if len(poles[i]) > n:
                smoothedF = poles[i][n]
                # add samples on both sides
                for j in range(1, s + 1):
                    # again, check that all values are defined
                    # (center point of smoothing might be defined, but parts of the window might not be!)
                    if len(poles[i + j]) > n and len(poles[i - j]) > n:
                        smoothedF += poles[i + j][n] + poles[i - j][n]
                    else:
                        # NOTE:  If part of the smoothing window is not defined, then no new value should be produced
                        # (equivalent to setting the value to "undefined" in Praat)
                        smoothedF = None
                        break
                # divide by window size (if all values were defined)
                if smoothedF != None:
                    new_poles[i - s].append(smoothedF / (2 * s + 1))
            # if center point itself is undefined
            else:
                continue

    return new_poles


def trimFormants(formants, times, minimum, maximum):
    """removes from the list of formants those values corresponding to the vowel transitions"""

    # used to remove vowel transitions for the Lennig and ANAE measurement
    # methods
    trimmedFormants = []
    trimmedTimes = []
    for i in range(len(formants)):
        if times[i] >= minimum and times[i] <= maximum:
            trimmedFormants.append(formants[i])
            trimmedTimes.append(times[i])

    return trimmedFormants, trimmedTimes

def window(iterable, window_len=2, window_step=1):
    """returns a tuple from an iterator"""
    iterators = tee(iterable, window_len)
    for skip_steps, itr in enumerate(iterators):
        for ignored in islice(itr, skip_steps):
            pass
    window_itr = zip(*iterators)
    if window_step != 1:
        window_itr = islice(window_itr, step=window_step)
    return window_itr


def whichSpeaker(speakers):
    """prompts the user for input on the speaker to be analyzed"""

    # if there are just two tiers in the input TextGrid, speakers will be an
    # empty list
    if not speakers:
        speaker = getSpeakerBackground("", 0)
        return speaker
    # get speaker from list of tiers
    print("Speakers in TextGrid:")
    for i, s in enumerate(speakers):
        print("%i.\t%s" % (i + 1, s))
    # user input is from 1 to number of speakers; index in speaker list one
    # less!
    speaknum = int(input("Which speaker should be analyzed (number)?  ")) - 1
    if speaknum not in range(len(speakers)):
        print("ERROR!  Please select a speaker number from 1 - %i.  " % (len(speakers) + 1))
        speaker = whichSpeaker(speakers)
        return speaker
    # plus, prompt for speaker background info and return speaker object
    else:
        speaker = getSpeakerBackground(speakers[speaknum], speaknum)
        return speaker


def writeLog(filename, wavFile, maxTime, meansFile, covsFile, opts):
    """writes a log file"""

    f = open(filename, 'w')
    f.write(time.asctime())
    f.write("\n")

    f.write("\n\n")

    f.write("extractFormants statistics for file %s:\n\n" %
            os.path.basename(wavFile))
    f.write("Total number of vowels (initially):\t%i\n" % count_vowels)
    if count_vowels:
        f.write("->\tNumber of vowels analyzed:\t%i\t(%.1f%%)\n" %
                (count_analyzed, float(count_analyzed) / float(count_vowels) * 100))
        f.write("->\tNumber of vowels discarded:\t%i\t(%.1f%%)\n" %
                ((count_vowels - count_analyzed), float((count_vowels - count_analyzed)) / float(count_vowels) * 100))
    f.write("\n")
    f.write("Duration of sound file:\t\t%.3f seconds\n" % maxTime)
    f.write("Time for program run:\t\t%.3f seconds\n" %
            (logtimes[-1][1] - logtimes[0][1]))
    if count_analyzed:
        f.write("->\t%.3f seconds per analyzed vowel\n" %
                ((logtimes[-1][1] - logtimes[0][1]) / count_analyzed))
    f.write("->\t%.3f times real time\n" %
            ((logtimes[-1][1] - logtimes[0][1]) / maxTime))
    f.write("\n")
    f.write("Excluded:\n")
    if count_vowels:
        f.write("- Uncertain transcriptions:\t\t%i\t(%.1f%%)\n" %
                (count_uncertain, float(count_uncertain) / float(count_vowels) * 100))
        f.write("- Overlaps:\t\t\t\t%i\t(%.1f%%)\n" %
                (count_overlaps, float(count_overlaps) / float(count_vowels) * 100))
        f.write("- Truncated words:\t\t\t%i\t(%.1f%%)\n" %
                (count_truncated, float(count_truncated) / float(count_vowels) * 100))
        f.write("- Below minimum duration:\t\t%i\t(%.1f%%)\n" %
                (count_too_short, float(count_too_short) / float(count_vowels) * 100))
    if removeStopWords and count_vowels:
        f.write("- Stop words:\t\t\t\t%i\t(%.1f%%)\n" %
                (count_stopwords, float(count_stopwords) / float(count_vowels) * 100))
    if not measureUnstressed and count_vowels:
        f.write("- Unstressed vowels:\t\t\t%i\t(%.1f%%)\n" %
                (count_unstressed, float(count_unstressed) / float(count_vowels) * 100))
    f.write("\n\n")
    f.write("extractFormant settings:\n")
    f.write("- removeStopWords:\t\t%s\n" % opts.removeStopWords)
    f.write("- measureUnstressed:\t\t%s\n" % (not opts.onlyMeasureStressed))
    f.write("- minVowelDuration:\t\t%.3f\n" % opts.minVowelDuration)
    f.write("- formantPredictionMethod:\t%s\n" % opts.formantPredictionMethod)
    f.write("- measurementPointMethod:\t%s\n" % opts.measurementPointMethod)
    f.write("- nFormants:\t\t\t%i\n" % opts.nFormants)
    f.write("- maxFormant:\t\t\t%i\n" % opts.maxFormant)
    f.write("- nSmoothing:\t\t\t%i\n" % opts.nSmoothing)
    f.write("- windowSize:\t\t\t%.3f\n" % opts.windowSize)
    f.write("- preEmphasis:\t\t\t%i\n" % opts.preEmphasis)
    f.write("- speechSoftware:\t\t%s\n" % opts.speechSoftware)
    f.write("- outputFormat:\t\t\t%s\n" % opts.outputFormat)
    f.write("- outputHeader:\t\t\t%s\n" % (not opts.noOutputHeader))
    f.write("- case:\t\t\t\t%s\n" % opts.case)
    f.write("- multipleFiles:\t\t%s\n" % opts.multipleFiles)
    f.write("- meansFile:\t\t\t%s\n" % opts.means)
    f.write("- covsFile:\t\t\t%s\n" % opts.covariances)
    f.write("- remeasurement:\t\t%s\n" % opts.remeasurement)
    f.write("- vowelSystem:\t\t%s\n" % opts.vowelSystem)
    f.write("- pickle\t\t%s\n" % opts.pickle)
    if opts.removeStopWords:
        f.write("- stopWords:\t\t\t%s\n" % opts.stopWords)
    f.write("\n\n")
    f.write("Time statistics:\n\n")
    f.write("count\ttime\td(time)\ttoken\n")
    for i in range(len(logtimes)):
        # chunk number and time stamp
        f.write(str(logtimes[i][0]) + "\t" + str(round(logtimes[i][1], 3)) + "\t")
        # delta time
        if i > 0:
            f.write(str(round(logtimes[i][1] - logtimes[i - 1][1], 3)) + "\t")
        # token
        f.write(logtimes[i][2])
        f.write("\n")
    f.close()
    print("\nWritten log file %s.\n" % filename)


#
# This used to be the main program; now it's wrapped in a function...     ##
#

def extractFormants(wavInput, tgInput, output, opts, SPATH='', PPATH=''):
    """run extractFormants on a sound file and TextGrid file, with the options specified in opts"""
    # S(OX)PATH and P(RAAT)PATH do not need to be specified when run as a standalone program (they can be verified via the shell),
    # but in some cases (running EF as a module from a CGI script as user
    # "www") this information is needed

    # initialize counters & timing
    global logtimes
    logtimes = []
    markTime("start")
    global count_vowels
    count_vowels = 0
    global count_analyzed
    count_analyzed = 0
    global count_uncertain
    count_uncertain = 0
    global count_overlaps
    count_overlaps = 0
    global count_truncated
    count_truncated = 0
    global count_stopwords
    count_stopwords = 0
    global count_unstressed
    count_unstressed = 0
    global count_too_short
    count_too_short = 0

    # if paths are specified, make them available globally
    global SOXPATH
    SOXPATH = SPATH
    global PRAATPATH
    PRAATPATH = PPATH

    # Add the applications directory to PATH
    # See https://github.com/JoFrhwld/FAVE/issues/53
    sys.path.append('/Applications')

    # set OS-specific variables
    global PRAATNAME
    if shutil.which('praat') is not None:
        PRAATNAME = 'praat'
    elif shutil.which('Praat') is not None:
        PRAATNAME = 'Praat'
    elif shutil.which('praatcon') is not None:
        PRAATNAME = 'praatcon'
    else:
        print("WARNING: unknown OS type '%s' may not be supported" % os.name)
        PRAATNAME = 'Praat'

    # by default, assume that these files are located in the current directory
    meansFile = opts.means
    covsFile = opts.covariances
    phonesetFile = opts.phoneset
    stopWordsFile = opts.stopWordsFile

    if stopWordsFile:
        opts.stopWords = parseStopWordsFile(stopWordsFile)

    # assign the options to individual variables and to type conversion if
    # necessary
    global case, outputHeader, outputFormat, formantPredictionMethod, measurementMethod, measurementPointMethod, nFormants#, maxFormant
    global nSmoothing, removeStopWords, measureUnstressed, minVowelDuration, windowSize, preEmphasis, multipleFiles, remeasurement, candidates, vowelSystem, tracks
    case = opts.case
    outputFormat = opts.outputFormat
    outputHeader = not opts.noOutputHeader
    formantPredictionMethod = opts.formantPredictionMethod
    measurementPointMethod = opts.measurementPointMethod
    mfa = opts.mfa
    speechSoftware = opts.speechSoftware
    nFormants = opts.nFormants
    #maxFormant = opts.maxFormant
    nSmoothing = opts.nSmoothing
    removeStopWords = opts.removeStopWords
    measureUnstressed = not opts.onlyMeasureStressed
    minVowelDuration = opts.minVowelDuration
    windowSize = opts.windowSize
    preEmphasis = opts.preEmphasis
    multipleFiles = opts.multipleFiles
    remeasurement = opts.remeasurement
    candidates = opts.candidates
    vowelSystem = opts.vowelSystem
    tracks = opts.tracks
    print("Processed options.")

    # read CMU phoneset ("cmu_phoneset.txt")
    phoneset = cmu.read_phoneset(opts.phoneset)
    print("Read CMU phone set.")

    # make sure the specified speech analysis program is in our path
    speechSoftware = checkSpeechSoftware(opts.speechSoftware)
    print("Speech software to be used is %s." % speechSoftware)

    # determine what program we'll use to extract portions of the audio file
    soundEditor = getSoundEditor()
    print("Sound editor to be used is %s." % soundEditor)

    # if we're using the Mahalanobis distance metric for vowel formant prediction,
    # we need to load files with the mean and covariance values
    if formantPredictionMethod == 'mahalanobis':
        global means, covs
        means = loadMeans(meansFile)  # "means.txt"
        covs = loadCovs(covsFile)  # "covs.txt"
        print("Read means and covs files for the Mahalanobis method.")

    # put the list of stop words in upper or lower case to match the word
    # transcriptions
    newStopWords = []
    for w in opts.stopWords:
        w = changeCase(w, case)
        newStopWords.append(w)
    opts.stopWords = newStopWords

    # for "multipleFiles" option:  read lists of files into (internal) lists
    if multipleFiles:
        wavFiles, tgFiles, outputFiles = processInput(wavInput, tgInput, output)
    else:
        wavFiles = [wavInput]
        tgFiles = [tgInput]
        outputFiles = [output]

    # process each tuple of input/output files
    for (wavFile, tgFile, outputFile) in zip(wavFiles, tgFiles, outputFiles):
        # make sure that we can find the input files, and that the TextGrid file is formatted properly
        # (functions will exit if files not formatted properly)
        checkWavFile(wavFile)
        checkTextGridFile(tgFile)

        # this will be used for the temporary files that we write
        fileStem = os.path.basename(wavFile).replace('.wav','')

        # load the information from the TextGrid file with the word and phone
        # alignments
        tg = praat.TextGrid()
        tg.read(tgFile)
        if opts.speaker:
            speaker = readSpeakerFile(opts.speaker)
            print("Read speaker background information from .speaker file.")
        else:
            speakers = checkTiers(tg, mfa)  # -> returns list of speakers
            # prompt user to choose speaker to be analyzed, and for background
            # information on the speaker
            speaker = whichSpeaker(speakers)  # -> returns Speaker object

        # adjust maximum formant frequency to speaker sex
        if speaker.sex in ["m", "M", "male", "MALE"]:
            opts.maxFormant = 5000
        elif speaker.sex in ["f", "F", "female", "FEMALE"]:
            opts.maxFormant = 5500
        else:
            sys.exit("ERROR!  Speaker sex undefined.")
        global maxFormant
        maxFormant = opts.maxFormant


        markTime("prelim1")
        # extract list of words and their corresponding phones (with all
        # coding) -> only for chosen speaker
        words = getWordsAndPhones(tg, phoneset, speaker, vowelSystem, mfa)
                                  # (all initial vowels are counted here)                                 
        print('Identified vowels in the TextGrid')
        global maxTime
        maxTime = tg.xmax()  # duration of TextGrid/sound file
        measurements = []

        markTime("prelim2")

        #if not opts.verbose:
            # n_words = len(words)
            # word_iter = 0
            # old_percent = 0

            # progressbar_width = 100
            # sys.stdout.write("\nExtracting Formants\n")
            # sys.stdout.write("[%s]" % (" " * progressbar_width))
            # sys.stdout.flush()
            # sys.stdout.write("\b" * (progressbar_width + 1))
            #                  # return to start of line, after '['

        pbar = tqdm(range(len(words)))
        for pre_w, w, fol_w in window(words, window_len = 3):


            # if not opts.verbose:
            #     word_iter = word_iter + 1
            #     new_percent = math.floor((float(word_iter) / n_words) * 100)

            #     for p in range(int(old_percent), int(new_percent)):
            #         sys.stdout.write("-")
            #         sys.stdout.flush()
            #         old_percent = new_percent

            # skip unclear transcriptions and silences
            if w.transcription == '' or w.transcription == "((xxxx))" or w.transcription.upper() == "SP":
                pbar.update(1)
                continue

            # convert to upper or lower case, if necessary
            w.transcription = changeCase(w.transcription, case)
            pre_w.transcription = changeCase(pre_w.transcription, case)
            fol_w.transcription = changeCase(fol_w.transcription, case)

            # if the word doesn't contain any vowels, then we won't analyze it
            numV = getNumVowels(w)
            if numV == 0:
                if opts.verbose:
                    print('')
                    print("\t\t\t...no vowels in word %s at %.3f." % (w.transcription, w.xmin))
                pbar.update(1)
                continue

            # don't process this word if it's in the list of stop words
            if removeStopWords and w.transcription in opts.stopWords:
                count_stopwords += numV
                if opts.verbose:
                    print('')
                    print("\t\t\t...word %s at %.3f is stop word." % (w.transcription, w.xmin))
                pbar.update(1)
                continue

            # exclude uncertain transcriptions
            if uncertain.search(w.transcription):
                count_uncertain += numV
                if opts.verbose:
                    print('')
                    print("\t\t\t...word %s at %.3f is uncertain transcription." % (w.transcription, w.xmin))
                pbar.update(1)
                continue

            for p_index, p in enumerate(w.phones):
                # skip this phone if it's not a vowel
                if not isVowel(p.label):
                    continue

                # exclude overlaps
                if p.overlap:
                    count_overlaps += 1
                    continue
                # exclude last syllables of truncated words
                if w.transcription[-1] == "-" and p.fs not in ['1', '2', '4', '5']:
                    count_truncated += 1
                    continue

                # skip this vowel if it doesn't have primary stress
                # and the user only wants to measure stressed vowels
                if not measureUnstressed and not hasPrimaryStress(p.label):
                    count_unstressed += 1
                    continue

                dur = round(p.xmax - p.xmin, 3)  # duration of phone

                # don't measure this vowel if it's shorter than the minimum length threshold
                # (this avoids an ESPS error due to there not being enough samples for the LPC,
                # and it leaves out vowels that are reduced)
                if dur < minVowelDuration:
                    count_too_short += 1
                    continue

                word_trans = " ".join([x.label for x in w.phones])
                pre_word_trans = " ".join([x.label for x in pre_w.phones])
                fol_word_trans = " ".join([x.label for x in fol_w.phones])
                p_context = ''
                pre_seg = ''
                fol_seg = ''

                if len(w.phones) == 1:
                    p_context = "coextensive"
                    try:
                        pre_seg = pre_w.phones[-1].label
                    except IndexError:
                        pre_seg = ''
                    try:
                        fol_seg = fol_w.phones[0].label
                    except IndexError:
                        fol_seg = ''
                elif p_index == 0:
                    p_context = "initial"
                    try:
                        pre_seg = pre_w.phones[-1].label
                    except IndexError:
                        pre_seg = ''
                    fol_seg = w.phones[p_index+1].label
                elif p_index is (len(w.phones)-1):
                    p_context = "final"

                    pre_seg = w.phones[p_index-1].label
                    try:
                        fol_seg = fol_w.phones[0].label
                    except IndexError:
                        fol_seg = ''
                else:
                    p_context = "internal"
                    pre_seg = w.phones[p_index-1].label
                    fol_seg = w.phones[p_index+1].label



                vowelFileStem = fileStem + '_' + \
                    p.label  # name of sound file - ".wav" + phone label
                vowelWavFile = vowelFileStem + '.wav'

                if opts.verbose:
                    print('')
                    print("Extracting formants for vowel %s in word %s at %.3f" % (p.label, w.transcription, w.xmin))

                markTime(count_analyzed + 1, p.label + " in " + w.transcription)

                # get padding for vowel in question
                padBeg, padEnd = getPadding(p, windowSize, maxTime)
                ## p = phone
                # windowSize:  from config file or default settings
                # maxTime = duration of sound file/TextGrid

                extractPortion(wavFile, vowelWavFile, p.xmin - padBeg, p.xmax + padEnd, soundEditor)

                vm = getVowelMeasurement(vowelFileStem, p, w, opts.speechSoftware,
                                         formantPredictionMethod, measurementPointMethod, nFormants, maxFormant, windowSize, preEmphasis, padBeg, padEnd, speaker)

                if vm:  # if vowel is too short for smoothing, nothing will be returned
                    vm.context = p_context
                    vm.pre_seg = pre_seg
                    vm.fol_seg = fol_seg
                    vm.p_index = str(p_index+1)
                    vm.word_trans = word_trans
                    vm.pre_word_trans = pre_word_trans
                    vm.fol_word_trans = fol_word_trans
                    vm.pre_word = pre_w.transcription
                    vm.fol_word = fol_w.transcription
                    measurements.append(vm)
                    count_analyzed += 1
            pbar.update(1)
        pbar.close()
        if remeasurement and formantPredictionMethod == 'mahalanobis':
            measurements = remeasure(measurements)

        # don't output anything if we didn't take any measurements
        # (this prevents the creation of empty output files)
        # if len(measurements) > 0:
        # calculate measurement means
        m_means = calculateMeans(measurements)
        # normalize measurements
        measurements, m_means = normalize(measurements, m_means)
        print('')
        outputMeasurements(outputFormat, measurements, m_means, speaker, outputFile, outputHeader, opts.tracks)

        if opts.pickle:
            pi = open(os.path.splitext(outputFile)[0] + ".pickle", 'w')
            pickle.dump(measurements, pi, pickle.HIGHEST_PROTOCOL)
            pi.close()

        markTime("end")

        # write log file
        writeLog(os.path.splitext(outputFile)
                 [0] + ".formantlog", wavFile, maxTime, meansFile, covsFile, opts)

def main():
    parser = setup_parser()

    opts = parser.parse_args()
    wavInput = opts.wavInput
    tgInput = opts.tgInput
    output = opts.output

    extractFormants(wavInput, tgInput, output, opts)

#
# MAIN PROGRAM STARTS HERE                         ##
#
if __name__ == '__main__':
    main()
