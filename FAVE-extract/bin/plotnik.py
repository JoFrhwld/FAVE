#
# !!! This is NOT the original plotnik.py file !!!                  ##
#
# Last modified by Ingrid Rosenfelder:  February 10, 2012                            ##
# - mostly comments (all comment beginning with a double pound sign ("##"))          ##
# - some closing of file objects                                                     ##
# - docstrings for all classes and functions                                         ##
# - changed order of contents:  (alphabetical within categories)                     ##
# 1. regexes & dictionaries                                                       ##
# 2. classes                                                                      ##
# 3. functions                                                                    ##
# - modified outputPlotnikFile:                                                      ##
# + style coding (converted to corresponding Plotnik codes)                       ##
# + [original LPC measurement values (poles and bandwidths) - commented out]      ##
# + nFormants selected (between slashes)                                          ##
# - dictionary STYLES (letters vs. Plotnik codes)                                    ##
# - added ethnicity and location to PltFile object, and changed outputPlotnikFile    ##
# - added phila_system                                                               ##
# - changed line endings to '\r' in .plt and .pll output files                       ##
# - changed "phila_system" to separate option                                        ##
# - fixed weird alignment case where word ended in "sp" phone                        ##
# - changed "philaSystem" option to "vowelSystem" with new option "simplifiedARPABET"##
# - formant "tracks" (5 points throughout the vowel) output in <> in .plt file       ##
#

import sys
import os
import string
import re

glide_regex = re.compile('{[a-z0-9]*}')
                         # Plotnik glide coding: '{[f|b|i|m|s|d|br2|g}'
style_regex = re.compile('-[0-9]-')  # Plotnik stylistic levels:  '-[1-7]-'
comment_regex = re.compile('-- .*')  # Plotnik:  beginning of comment
count_regex = re.compile('[0-9]$')
                         # Plotnik:  number at end of token (for multiple
                         # tokens of same word):  '[0-9]+$'
stress_regex = re.compile(
    '[0-2]$')     # Arbabet coding:  primary stress, secondary stress, or unstressed (at end of vowel)

# "TRANSLATION" DICTIONARIES:
# Arpabet to Plotnik coding
A2P = {'AA': '5', 'AE': '3', 'AH': '6', 'AO': '53', 'AW': '42', 'AY': '41', 'EH': '2', 'ER':
       '94', 'EY': '21', 'IH': '1', 'IY': '11', 'OW': '62', 'OY': '61', 'UH': '7', 'UW': '72'}
A2P_FINAL = {'IY': '12', 'EY': '22', 'OW': '63'}
A2P_R = {'EH': '2', 'AE': '3', 'IH': '14', 'IY': '14', 'EY': '24', 'AA': '44', 'AO':
         '64', 'OW': '64', 'UH': '74', 'UW': '74', 'AH': '6', 'AW': '42', 'AY': '41', 'OY': '61'}
# CMU phoneset (distinctive features) to Plotnik coding
MANNER = {'s': '1', 'a': '2', 'f': '3', 'n': '4', 'l': '5', 'r': '6'}
PLACE = {'l': '1', 'a': '4', 'p': '5', 'b': '2', 'd': '3', 'v': '6'}
VOICE = {'-': '1', '+': '2'}

# style codes
STYLES = {"R": "2", "N": "1", "L": "2", "G": "1", "S": "2", "K":
          "1", "T": "1", "C": "2", "WL": "6", "MP": "7", "RP": "5", "SD": "4"}
# Plotnik vowel classes (in the order that they appear in the Plotnik side bar)
PLOTNIKCODES = [
    '1', '2', '3', '5', '6', '7', '8', '11', '12', '21', '22', '41', '47', '61', '82',
    '72', '73', '62', '63', '42', '33', '43', '53', '14', '24', '44', '54', '64', '74', '94', '31', '39']

# ARPABET phonesets
CONSONANTS = ['B', 'CH', 'D', 'DH', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M',
              'N', 'NG', 'P', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'Y', 'Z', 'ZH']
VOWELS = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH',
          'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
SPECIAL = ['BR', 'CG', 'LS', 'LG', 'NS']

#


class PltFile:

    """represents a Plotnik file (header and vowel measurements)"""

    def __init__(self):
        # header - speaker information
        self.first_name = ''  # first name of speaker
        self.last_name = ''  # last name of speaker
        self.age = ''  # speaker age
        self.city = ''  # city
        self.state = ''  # state
        self.sex = ''  # speaker sex
        self.ethnicity = ''  # ethnicity
        self.location = ''  # location (e.g. street name)
        self.years_of_schooling = ''  # years of schooling completed
        self.ts = ''  # Telsur number (just the number, without "TS"/"ts")
        self.year = ''  # year of recording
        # second header line
        self.N = ''  # number of tokens in file
        self.S = ''  # group log mean for nomalization (ANAE p. 39) ??? - or individual log mean ???
        # tokens
        self.measurements = []
            # list of measurements (all following lines in Plotnik file)
        self.means = {}  # means and standard deviations for each vowel class

    def __str__(self):
        return """<Plotnik file for speaker %s %s (%s, %s, %s, %s years of schooling, from %s, recorded in %s) with %s tokens.>""" % (self.first_name, self.last_name, self.age, self.sex, self.ethnicity, self.years_of_schooling, self.location, self.year, self.N)


class VowelMeasurement:

    """represents a single vowel token (one line in a Plotnik data file)"""
    F1 = 0  # first formant
    F2 = 0  # second formant
    F3 = ''  # third formant
    code = ''  # Plotnik code for vowel class (includes phonetic environment):  "xx.xxxxx"
    stress = 1  # level of stress (default = primary) (and duration:  "x.xxx"???)
    text = ''  # rest of line (everything that is not numbers:  token/word, glide, style, comment, ...)
    word = ''  # (orthographic) transcription of token (with parentheses and count)
    trans = ''  # normal transcription (without parentheses and count, upper case)
    fname = ''  # 8-character token identifier???
    comment = ''  # Plotnik comment (everything after " -- ")
    glide = ''  # Plotnik coding for glide (if present)
    style = ''  # Plotnik coding for stylistic level (if present)
    t = 0  # time of measurement


def arpabet2plotnik(ac, trans, prec_p, foll_p, phoneset, fm, fp, fv, ps, fs):
    """translates Arpabet transcription of vowels into codes for Plotnik vowel classes"""
    # ac = Arpabet coding (without stress digit)
    # trans = (orthographic) transcription of token
    # prec_p = preceding phone
    # foll_p = following phone
    # phoneset = CMU phoneset (distinctive features)
    # pc = Plotnik code

#  print "\tac:  %s\tprec_p:  %s\tfoll_p:  %s\tfm:  %s\tfp:  %s\tfv:  %s\tps:  %s\tfs:  %s\ttrans:  %s"  % (ac, prec_p, foll_p, fm, fp, fv, ps, fs, trans)
#  print ','.join([ac, prec_p, foll_p, fm, fp, fv, ps, fs, trans])

    # if different consonant inventories are used, just use the plain
    # conversions
    if (prec_p not in phoneset and prec_p != '') or (foll_p not in phoneset and foll_p != ''):
        pc = A2P[ac]

    # free vs. checked vowels  -> iyF, eyF, owF:
    elif foll_p == '' and ac in ['IY', 'EY', 'OW']:
        pc = A2P_FINAL[ac]
    # Canadian Raising -> ay0:
    elif foll_p != '' and ac == 'AY' and phoneset[foll_p].cvox == '-':
        pc = '47'
    # ingliding ah:
    elif ac == 'AA' and trans in ['FATHER', 'FATHER', "FATHER'S", 'MA', "MA'S", 'PA', "PA'S", 'SPA', 'SPAS', "SPA'S",
                                  'CHICAGO', "CHICAGO'S", 'PASTA', 'BRA', 'BRAS', "BRA'S", 'UTAH', 'TACO', 'TACOS', "TACO'S",
                                  'GRANDFATHER', 'GRANDFATHERS', "GRANDFATHER'S", 'CALM', 'CALMER', 'CALMEST', 'CALMING', 'CALMED', 'CALMS',
                                  'PALM', 'PALMS', 'BALM', 'BALMS', 'ALMOND', 'ALMONDS', 'LAGER', 'SALAMI', 'NIRVANA', 'KARATE', 'AH']:
        pc = '43'
    # uw after coronal onsets -> Tuw:
    elif prec_p != '' and ac == 'UW' and phoneset[prec_p].cplace == 'a':
        pc = '73'
    # Vhr subsystem (following tautosyllabic r):
    # (no distinction between ohr and owr)
    elif foll_p != ''and phoneset[foll_p].ctype == 'r' and ac != 'ER':
        pc = A2P_R[ac]
    # all other cases:
    else:
        pc = A2P[ac]

    return pc


def cmu2plotnik_code(i, phones, trans, phoneset, speaker, vowelSystem):
    """converts Arpabet to Plotnik coding (for vowels) and adds Plotnik environmental codes (.xxxxx)"""
    # i = index of vowel in token
    # phones = list of phones in whole token
    # trans = transcription (label) of token
    # phoneset = CMU phoneset (distinctive features)

    # don't do anything if it's a consonant
    if not is_v(phones[i].label):
        return None, None

    # FOLLOWING SEGMENT:
    # if the vowel is the final phone in the list, then there is no following segment
    # (second condition is for word-final "SP" phone (extremely rare but it has happened))
    if (i + 1 == len(phones)) or ((i == len(phones) - 2) and (phones[i + 1].label.upper() == "SP")):
        foll_p = ''  # following segment:
        fm = '0'  # - following manner (code)
        fp = '0'  # - following place (code)
        fv = '0'  # - following voice (code)
        fs = '0'  # following sequence (code)
    else:
        # get the following segment, and strip the stress code off if it's a
        # vowel
        foll_p = re.sub(stress_regex, '', phones[i + 1].label)
        try:
            ctype = phoneset[foll_p].ctype
            cplace = phoneset[foll_p].cplace
            cvox = phoneset[foll_p].cvox
        except KeyError:
            ctype = '0'
            cplace = '0'
            cvox = '0'
        # convert from the CMU codes to the Plotnik codes
        fm = MANNER.get(ctype, '0')  # get value for key,
        fp = PLACE.get(cplace, '0')  # "0": default if key does not exist
        fv = VOICE.get(cvox, '0')
                       # from MANNER, PLACE, VOICE dictionaries above
        # FOLLOWING SEQUENCE:
        n_foll_syl = get_n_foll_syl(i, phones)  # number of following syllables
        n_foll_c = get_n_foll_c(i, phones)  # number of consonants in coda
        if n_foll_c <= 1 and n_foll_syl == 1:
            fs = '1'  # one following syllable
        elif n_foll_c <= 1 and n_foll_syl >= 2:
            fs = '2'  # two following syllables
        elif n_foll_c > 1 and n_foll_syl == 0:
            fs = '3'  # complex coda
        elif n_foll_c > 1 and n_foll_syl == 1:
            fs = '4'  # complex coda + 1 syllable
        elif n_foll_c > 1 and n_foll_syl >= 2:
            fs = '5'  # complex coda + 2 syllables
        else:
            fs = '0'

    # PRECEDING SEGMENT:
    # if the vowel is the first phone in the list, then there is no preceding
    # segment
    if i == 0:
        prec_p = ''  # preceding phone
        ps = '0'  # preceding segment (code)
    else:
        # get the preceding segment, and strip the stress code off if it's a
        # vowel
        prec_p = re.sub(stress_regex, '', phones[i - 1].label)
        if prec_p in ['B', 'P', 'V', 'F']:
            ps = '1'  # oral labial
        elif prec_p in ['M']:
            ps = '2'  # nasal labial
        elif prec_p in ['D', 'T', 'Z', 'S', 'TH', 'DH']:
            ps = '3'  # oral apical
        elif prec_p in ['N']:
            ps = '4'  # nasal apical
        elif prec_p in ['ZH', 'SH', 'JH', 'CH']:
            ps = '5'  # palatal
        elif prec_p in ['G', 'K']:
            ps = '6'  # velar
        elif i > 1 and prec_p in ['L', 'R'] and phones[i - 2].label in ['B', 'D', 'G', 'P', 'T', 'K', 'V', 'F', 'Z', 'S', 'SH', 'TH']:
            ps = '8'  # obstruent + liquid
        elif prec_p in ['L', 'R', 'ER']:
            ps = '7'  # liquid
        elif prec_p in ['W', 'Y']:
            ps = '9'  # /w/, /y/
        else:
            ps = '0'

    # convert CMU (Arpabet) transcription into Plotnik code
    # ("label[:-1]":  without stress digit)
    code = arpabet2plotnik(re.findall(r'^([A-Z]{2,2})\d?$', phones[i].label.upper())[
                           0], trans, prec_p, foll_p, phoneset, fm, fp, fv, ps, fs)

    # adjust vowel class assignment for Philadelphia system
#  try:
# if (os.path.basename(filename)[:2].upper() == 'PH') or
# (os.path.basename(filename).split('_')[2][:2].upper() == 'PH') or
# (speaker.city in ['Philadelphia', 'Phila', 'PHILADELPHIA', 'Philly'] and
# speaker.state in ['PA', 'pa']):
    if vowelSystem.upper() == 'PHILA':
        code = phila_system(
            i, phones, trans, fm, fp, fv, ps, fs, code, phoneset)
# except IndexError:  ## if file is not uploaded via the web site and has identifier at beginning, the filename split will cause an error
#    pass

    # add Plotnik environmental coding
    code += '.'
    code += fm
    code += fp
    code += fv
    code += ps
    code += fs

    return code, prec_p


def convertDur(dur):
    """converts durations into integer msec (as required by Plotnik)"""
    dur = int(round(dur * 1000))
    return dur


def convertStress(stress):
    """converts labeling of unstressed vowels from '0' in the CMU Pronouncing Dictionary to '3' in Plotnik"""
    if stress == '0':
        stress = '3'
    return stress


def get_age(line):
    """returns age of speaker from header line of Plotnik file, if present"""
    try:
        age = line.split(',')[1].strip()  # second data field
    except IndexError:
        age = ''
    return age


def get_city(line):
    """returns city from header line of Plotnik file, if present"""
    sex = get_sex(line)
    if sex in ['m', 'f']:  # if sex included as third data field, city is in forth
        try:
            city = line.split(',')[3].strip()
        except IndexError:
            city = ''
    else:  # otherwise, look in third data field
        try:
            city = line.split(',')[2].strip()
        except IndexError:
            city = ''
    return city


def get_first_name(line):
    """returns first name of speaker from header line of Plotnik file"""
    first_name = line.split(',')[0].split()[
        0]  # first part of first data field
    return first_name


def get_last_name(line):
    """returns last name of speaker from header line of Plotnik file, if present"""
    try:
        last_name = line.split(',')[0].split()[
            1]  # second part of first data field
    except IndexError:
        last_name = ''
    return last_name


def get_n(line):
    """returns number of tokens from second header line of Plotnik file, if present"""
    try:
        n = int(line.strip().split(',')[0])
    except IndexError:
        n = ''
    return n


def get_n_foll_c(i, phones):
    """returns the number of consonants in the syllable coda"""
    # i = index of vowel phoneme in question
    # phones = complete list of phones in word/token
    n = 0
    for p in phones[i + 1:]:
        if is_v(p.label):
            break
        elif n == 1 and p.label in ['Y', 'W', 'R', 'L']:  # e.g. 'figure', 'Wrigley', etc.
            break
        else:
            n += 1
    return n


def get_n_foll_syl(i, phones):
    """returns the number of following syllables"""
    # number of syllables determined by number of following vowels
    # i = index of vowel phoneme in question
    # phones = complete list of phones in word/token
    n = 0
    for p in phones[i + 1:]:
        if is_v(p.label):
            n += 1
    return n


def get_s(line):
    """returns ??? from second header line of Plotnik file, if present"""
    try:
        s = float(line.strip().split(',')[1])
    except IndexError:
        s = ''
    return s


def get_sex(line):
    """returns speaker sex from header line of Plotnik file, if included"""
    try:
        sex = line.split(',')[2].strip()
                         # sex would be listed in third data field
    except IndexError:
        sex = ''
    # only some files have sex listed in the first line
    if sex not in ['m', 'f']:  # if contents of third data field somthing other than sex (e.g. city)
        sex = ''
    return sex


def get_state(line):
    """returns state from header line of Plotnik file, if present"""
    sex = get_sex(line)
    if sex in ['m', 'f']:  # if sex included as third data field, state is in fifth
        try:
            state = line.split(',')[4].strip().split()[0]
        except IndexError:
            state = ''
    else:  # otherwise, look in forth data field
        try:
            state = line.split(',')[3].strip().split()[0]
        except IndexError:
            state = ''
    return state


def get_stressed_v(phones):
    """returns the index of the stressed vowel, or '' if none or more than one exist"""
    primary_count = 0
    for p in phones:
        if p[-1] == '1':
            primary_count += 1
            i = phones.index(p)
    # if there is more than vowel with primary stress in the transcription,
    # then we don't know which one to look at, so return ''
    if primary_count != 1:
        return ''
    else:
        return i


def get_ts(line):
    """returns Telsur subject number from header line of Plotnik file, if present"""
    if ' TS ' in line:
        ts = line.strip().split(' TS ')[
            1]  # returns only the number, not "TS"/"ts"
    elif ' ts ' in line:
        ts = line.strip().split(' ts ')[1]
    else:
        ts = ''
    return ts


# this is a hack based on the fact that we know that the CMU transcriptions for vowels
# all indicate the level of stress in their final character (0, 1, or 2);
# will rewrite them later to be more portable...
# this function sometimes causes index errors!
# def is_v(p):
##  """checks whether a given phone is a vowel (based on final code for stress from CMU dictionary)"""
# if p[-1] in ['0', '1', '2']:
# return True
# else:
# return False

def is_v(label):
    """checks whether a phone is a vowel"""
    # use the vowel inventory instead!
    if re.findall(r'^([A-Z]{2,2})\d?$', label.upper()) and re.findall(r'^([A-Z]{2,2})\d?$', label.upper())[0] in VOWELS:
        return True
    else:
        return False


def outputPlotnikFile(Plt, f):
    """writes the contents of a PltFile object to file (in Plotnik format)"""

    # NOTE:  Plotnik/SuperCard requires the use of '\r', NOT '\n', as the
    # end-of-line delimiter!!!s

    ## pltFields = {'f1':0, 'f2':1, 'f3':2, 'code':3, 'stress':4, 'word':5}
    fw = open(f, 'w')
    # header
    #fw.write(" ".join([Plt.first_name, Plt.last_name]) + ',' + ','.join([Plt.age, Plt.sex, Plt.city, Plt.state, Plt.ts]))
    fw.write(" ".join([Plt.first_name, Plt.last_name]) + ',' + ','.join(
        [Plt.age, Plt.sex, Plt.ethnicity, Plt.years_of_schooling, Plt.location, Plt.year]))
    fw.write('\r')
    fw.write(str(Plt.N) + ',' + str(Plt.S))  # no spaces around comma here!
    fw.write('\r')
    # end of header
    # measurements for individual tokens
    for vm in Plt.measurements:
        stress = convertStress(vm.stress)
        dur = convertDur(vm.dur)
        if not vm.f3:
            vm.f3 = ''
        if vm.f2:  # F1, F2, F3, vowel and environmental coding, stress and duration, token
            fw.write(
                ','.join([str(round(vm.f1, 1)), str(round(vm.f2, 1)), str(vm.f3), vm.code, stress + '.' + str(dur), vm.word]))
        else:  # (for undefined F2)
            fw.write(
                ','.join([str(round(vm.f1, 1)), str(vm.f2), str(vm.f3), vm.code, stress + '.' + str(dur), vm.word]))
        if vm.glide:
            fw.write(' {' + vm.glide + '}')  # glide annotation, if applicable
        if vm.style:
            fw.write(' -' + style2plotnik(vm.style, vm.word) + '-')
                     # style coding, if applicable
        if vm.nFormants:
            fw.write(' /' + str(vm.nFormants) + '/')
                     # nFormants (if Mahalanobis method)
        fw.write(' ' + str(vm.t) + ' ')  # measurement point
# fw.write('+' + ','.join([str(p) for p in vm.poles]) + '+')        ## list of original poles as returned from LPC analysis (at point of measurement)
# fw.write('+' + ','.join([str(b) for b in vm.bandwidths]) + '+')   ##
# list of original bandwidths as returned from LPC analysis (at point of
# measurement)
        fw.write(
            ' <' + ','.join([str(round(t, 0)) if t else '' for t in vm.tracks]) + '>')
        fw.write('\r')
    # means and standard deviations for each vowel class
    fw.write('\r')
    for p in PLOTNIKCODES:
        fw.write(
            ','.join([p, str(max([len(Plt.means[p].values[i]) for i in range(3)])),
                      str(Plt.means[p].means[0]), str(
                          Plt.means[p].means[1]), str(
                          Plt.means[p].means[2]),
                      str(Plt.means[p].stdvs[0]), str(Plt.means[p].stdvs[1]), str(Plt.means[p].stdvs[2])]))
        fw.write(
            ' <' + ','.join([str(round(t[0], 0)) if t[0] else '' for t in Plt.means[p].trackmeans]) + '>')
        fw.write('\r')
    fw.close()
    print "Vowel measurements output in .plt format to the file %s" % (f)

    # normalized values
    ff = os.path.splitext(f)[0] + ".pll"
    fw = open(ff, 'w')
    # header
    fw.write(" ".join([Plt.first_name, Plt.last_name]) + ',' + ','.join(
        [Plt.age, Plt.sex, Plt.ethnicity, Plt.years_of_schooling, Plt.location, Plt.year]))
    fw.write('\r')
    fw.write(str(Plt.N) + ',' + str(Plt.S))  # no spaces around comma here!
    fw.write('\r')
    # measurements for individual tokens
    for vm in Plt.measurements:
        stress = convertStress(vm.stress)
        dur = convertDur(vm.dur)
        if not vm.norm_f3:
            vm.norm_f3 = ''
        if vm.norm_f2:  # F1, F2, F3, vowel and environmental coding, stress and duration, token
            fw.write(
                ','.join([str(round(vm.norm_f1, 1)), str(round(vm.norm_f2, 1)), str(vm.norm_f3), vm.code, stress + '.' + str(dur), vm.word]))
        else:
            fw.write(
                ','.join([str(round(vm.norm_f1, 1)), str(vm.norm_f2), str(vm.norm_f3), vm.code, stress + '.' + str(dur), vm.word]))
        if vm.glide:
            fw.write(' {' + vm.glide + '}')  # glide annotation, if applicable
        if vm.style:
            fw.write(' -' + style2plotnik(vm.style, vm.word) + '-')
                     # style coding, if applicable
        if vm.nFormants:
            fw.write(' /' + str(vm.nFormants) + '/')
                     # nFormants (if Mahalanobis method)
        fw.write(' ' + str(vm.t) + ' ')  # measurement point
        fw.write(
            ' <' + ','.join([str(round(t, 0)) if t else '' for t in vm.norm_tracks]) + '>')
        fw.write('\r')

    # means and standard deviations for each vowel class
    fw.write('\r')
    for p in PLOTNIKCODES:
        fw.write(
            ','.join([p, str(max([len(Plt.means[p].values[i]) for i in range(3)])),
                      str(Plt.means[p].norm_means[0]), str(
                          Plt.means[p].norm_means[1]), str(
                          Plt.means[p].norm_means[2]),
                      str(Plt.means[p].norm_stdvs[0]), str(Plt.means[p].norm_stdvs[1]), str(Plt.means[p].norm_stdvs[2])]))
        fw.write(
            ' <' + ','.join([str(round(t[0], 0)) if t[0] else '' for t in Plt.means[p].trackmeans_norm]) + '>')
        fw.write('\r')
    fw.close()
    print "Normalized vowel measurements output in .pll format to the file %s" % (os.path.splitext(f)[0] + ".pll")


def phila_system(i, phones, trans, fm, fp, fv, ps, fs, pc, phoneset):
    """redefines vowel classes for Philadelphia"""

    orig_pc = pc  # Plotnik code returned by arpabet2plotnik
    phones = split_stress_digit(
        phones)  # separate Arpabet coding from stress digit for vowels

    # 1. /aeh/ and /aey/:  tense and variable short-a
    if pc == '3' and phones[i].label == "AE1" and trans.upper() not in ['AND', "AN'", 'AM', 'AN', 'THAN'] and fm != '0':

        # /aeh/:  tense short-a

        # following front nasals, voiceless fricatives
        if phones[i + 1].arpa in ['M', 'N', 'S', 'TH', 'F']:
            # tensing consonants word-finally
            if len(phones) == i + 2:
                if trans.upper() in ['MATH']:
                    pc = '39'
                else:
                    pc = '33'  # e.g. "man", "ham"
            # tensing consonants NOT word-finally
            elif len(phones) > i + 2:
                # AE1 ['M', 'N', 'S', 'TH', 'F'] followed by another consonant
                # (e.g. "hand", "classroom")
                if (phoneset[phones[i + 2].arpa].cvox != '0') and trans.upper() not in ['CATHOLIC', 'CATHOLICS', 'CAMERA']:
                    pc = '33'
                # AE1 ['M', 'N', 'S', 'TH', 'F'] followed by a vowel
                else:
# following suffix -er
# if phones[i+2] == 'ER0':
##            pc = '33'
                    # following suffixes -ing, -in', -es ("manning")
                    if len(phones) > i + 3:
                        a = phones[i + 2].label
                        b = phones[i + 3].label
                        ab = [a, b]
                        # print "Suffix for word %s is %s." % (trans, ab)
                        if len(phones) == i + 4 and ab in [['IH0', 'NG'], ['AH0', 'NG'], ['AH0', 'N'], ['AH0', 'Z']]:
                            pc = '33'
                        # all other vowels
                        else:
                            pc = '39'

        # mad, bad, glad and derived forms
        if trans.upper(
        ) in ['MAD', 'BAD', 'GLAD', 'MADLY', 'BADLY', 'GLADLY', 'MADDER', 'BADDER', 'GLADDER',
              'MADDEST', 'BADDEST', 'GLADDEST', 'MADNESS', 'GLADNESS', 'BADNESS', 'MADHOUSE']:
            pc = '33'

        # /aey/:  variable short-a

        if trans.upper(
        ) in ['RAN', 'SWAM', 'BEGAN', 'CAN', 'FAMILY', 'FAMILIES', "FAMILY'S", 'JANUARY', 'ANNUAL',
              'ANNE', "ANNE'S", 'ANNIE', "ANNIE'S", 'JOANNE', 'GAS', 'GASES', 'EXAM', 'EXAMS', "EXAM'S", 'ALAS', 'ASPIRIN']:
            pc = '39'

        # following /l/
        if phones[i + 1].arpa == 'L':
            pc = '39'

        # -SKV- words, e.g. "master", "rascal", "asterisk"
        if len(phones) > i + 3 and phones[i + 1].arpa == 'S' and phones[i + 2].arpa in ['P', 'T', 'K'] and phoneset[phones[i + 3].arpa].cvox == '0':
            if trans[-3:] not in ["ING", "IN'"]:  # exclude final "-ing"/"-in'" words, e.g. "asking"
                pc = '39'
# -NV- words, e.g. "planet", "Janet", "hammer", and "-arry" words, e.g. "marry", "carry", "Harold"
# if len(phones) > i + 2 and phones[i+1].arpa in ['N' 'M', 'R'] and phoneset[phones[i+2].arpa].cvox == '0':
# if trans[-3:] not in ["ING", "IN'"]:  ## exclude final "-ing"/"-in'" words, e.g. "planning"
##        pc = '39'

    # convert dictionary entries to short-a for "-arry" words
    if pc == '2' and 'ARRY' in trans.upper():
        if len(phones) > i + 2 and phones[i + 1].arpa == 'R' and phoneset[phones[i + 2].arpa].cvox == '0':
            pc = '39'

    # random dictionary inaccuracies
    if pc == '5' and trans.upper() == 'MARIO':
        pc = '3'

    # 2. /e/
    if trans.upper() in ["CATCH", "KEPT"]:
        pc = '2'

    # 3. /oh/
    if phones[
        i].arpa == 'AA' and trans.upper() in ['LAW', 'LAWS', "LAW'S", 'LAWFUL', 'UNLAWFUL', 'DOG', 'DOGS', "DOG'S", 'DOGGED',
                                              'ALL', "ALL'S", 'CALL', 'CALLS', "CALL'S", 'CALLING', 'CALLED', 'FALL', 'FALLS', "FALL'S", 'FALLING'
                                              'AUDIENCE', 'AUDIENCES', "AUDIENCE'S", 'ON', 'ONTO', 'GONNA', 'GONE', 'BOSTON', "BOSTON'S",
                                              'AWFUL', 'AWFULLY', 'AWFULNESS', 'AWKWARD', 'AWKWARDLY', 'AWKWARDNESS', 'AWESOME', 'AUGUST',
                                              'COUGH', 'COUGHS', 'COUGHED', 'COUGHING']:
        pc = '53'

    # 4. /o/
    if phones[
        i].arpa == 'AO' and trans.upper() in ['CHOCOLATE', 'CHOCOLATES', "CHOCOLATE'S", 'WALLET', 'WALLETS', 'WARRANT', 'WARRANTS',
                                              'WATCH', 'WATCHES', 'WATCHED', 'WATCHING', 'WANDER', 'WANDERS', 'WANDERED', 'WANDERING',
                                              'CONNIE', 'CATHOLICISM', 'WANT', 'WANTED', 'PONG', 'GONG', 'KONG', 'FLORIDA', 'ORANGE',
                                              'HORRIBLE', 'MAJORITY']:
        pc = '5'

    if phones[i].arpa == 'AE' and trans.upper() in ['LANZA', "LANZA'S"]:
        pc = '5'

# 4. /ah/
# if pc == '5' and phones[i].arpa == 'AA' and (i > 0 and phones[i-1].arpa != 'W') and (len(phones) != i+1 and phones[i+1].arpa != 'R'):
##    x1 = max(0, i - 3)
##    x2 = min(len(trans), i + 3)
# print "Checking a spelling in chunk %s of word %s (%s)." % (trans[x1:x2].upper(), trans, ' '.join([p.label for p in phones]))
# for t in ['AU', 'AW', 'AL']:
# if 'A' in trans[x1:x2].upper() and t not in trans[x1:x2].upper():
##        pc = '43'

    # 5. /iw/
    if phones[i].label == "UW1":
        # UW1 preceded by /y/
        if i > 0 and phones[i - 1].arpa == 'Y':
            pc = '82'
        # words spelled with "-ew", e.g. "threw", "new", "brew"
        if 'EW' in trans.upper():
            pc = '82'
        # words spelled with "-u" after /t/, /d/, /n/, /l/, /s/, e.g.
        # "Tuesday", "nude", "duty", "new"
        if i > 0 and phones[i - 1].arpa in ['T', 'D', 'N', 'L', 'S']:
            for t in ['TU', 'DU', 'NU', 'LU', 'SU']:  # make sure -u spelling is adjacent to consonant in orthography
                if t in trans.upper():
                    pc = '82'

    # 6. /Tuw/
    if phones[i].label == "UW1" and trans.upper in ['THROUGH']:
        pc = '73'

# if pc != orig_pc:
# print "\tPhila system reassignment:  Changed class of vowel %s from %2s
# to %2s in word %s (%s)." % (phones[i].label, orig_pc, pc, trans, '
# '.join([p.label for p in phones]))

    # 7. front vowels before r
    if len(phones) > i + 1 and phones[i].arpa in ['EH', 'AE'] and phones[i + 1].arpa == 'R':
        if len(phones) == i + 2:  # word-final /r/
            pc = '24'
        if len(phones) > i + 2 and phoneset[phones[i + 2].arpa].cvox != '0':  # not word-final but also NOT intervocalic r
            pc = '24'

    return pc


def process_measurement_line(line):
    """splits Plotnik measurement line into values for formants, vowel class, stress, token, glide, style, and comment"""
    vm = VowelMeasurement()
    vm.F1 = float(line.split(',')[0])  # first formant
    vm.F2 = float(line.split(',')[1])  # second formant
    try:
        vm.F3 = float(line.split(',')[2])  # third formant, if present
    except ValueError:
        vm.F3 = ''
    vm.code = line.split(',')[
        3]  # Plotnik vowel code (includes phonetic environment):  "xx.xxxxx"
    vm.stress = line.split(',')[4]  # stress (and duration:  "x.xxx"???)
    vm.text = line.split(',')[5]  # rest of line (word, glide, style, comment)
                                          # if TIME STAMP was included in file, it would be in field 6!
                                          # -> check number of fields returned from split(',')!
    # process text
    vm.word = vm.text.split()[0]  # token (with parentheses and count)
    vm.trans = word2trans(vm.word)
                          # translate token to normal transcription (without
                          # parentheses and count, upper case)
    vm.fname = word2fname(vm.word)  # translate token to ???unique filename???

    res = re.findall(glide_regex, vm.text)  # search for glide coding
    if len(res) > 0:  # if present:
        temp = res[0].replace('{', '')  # get rid of initial parenthesis
        temp = temp.replace('}', '')  # get rid of final parenthesis
        vm.glide = temp  # glide coding

    res = re.findall(style_regex, vm.text)  # search for style coding
    if len(res) > 0:  # if present:
        temp = res[0].replace('-', '')  # get rid of initial dash
        temp = temp.replace('-', '')  # get rid of final dash
        vm.style = temp  # style coding

    res = re.findall(comment_regex, vm.text)  # search for comment
    if len(res) > 0:  # if present:
        temp = res[0].replace('-- ', '')  # get rid of initial two dashes
        vm.comment = temp  # why should glide only be indicated in comment, not as glide coding?
        if temp == 'glide':
            vm.glide = 'g'
    else:
        res = style_regex.split(
            vm.text)  # split rest of line by style coding - WHY???
        if len(res) > 1:
            vm.comment = res[
                1].strip()  # anything that comes after the style coding

    return vm


def process_plt_file(filename):
    """reads a Plotnik data file into a PltFile object"""
    f = open(filename, 'rU')
    line = f.readline().strip()
                      # NOTE:  stripped of end-of-line character(s)! (see
                      # below)

    # skip initial blank lines
    while line == '':  # stripped line empty = no content
        line = f.readline()
                          # next line read - NOTE:  WITH end-of-line character(s)!
        # EOF was reached, so this file only contains blank lines
        if line == '':  # if not even end-of-line character in next line, then end of file reached
            f.close()  # (added)
            print "Closing empty file %s." % filename
            sys.exit()
        else:  # else:  strip end-of-line characters away,
            line = line.strip()
                              # and check for content again (beginning of loop)

    Plt = PltFile()

    # process first header line
##  Plt.first_name = get_first_name(line)
##  Plt.last_name = get_last_name(line)
##  Plt.age = get_age(line)
##  Plt.sex = get_sex(line)
##  Plt.city = get_city(line)
##  Plt.state = get_state(line)
##  Plt.ts = get_ts(line)
    headerfields = line.split(',')
    Plt.first_name = headerfields[
        0]  # just put the whole name into Plt.first_name and do not bother about splitting
    Plt.age = headerfields[1]
    Plt.sex = headerfields[2]
    Plt.ethnicity = headerfields[3]
    Plt.years_of_schooling = headerfields[4]
    Plt.location = headerfields[5]
    Plt.year = headerfields[6]

    # process second header line
    line = f.readline().strip()
##  Plt.N = get_n(line)
##  Plt.S = get_s(line)
    Plt.N = line.split(',')[0]

    # data lines next...
    line = f.readline().strip()

    # again, check for blank lines:
    # skip any blank lines between header and formant measurements
    while line == '':
        line = f.readline()
        # this file only contains blank lines
        if line == '':
            f.close()  # (added)
            print "Closing file %s (no measurements)." % filename
            sys.exit()
        else:
            line = line.strip()

    Plt.measurements = []
    fields = []

    # proceed until we reach the blank line separating the formant data from
    # the means
    while line != '':
       # some files don't contain this blank line, so look to see if the first value in the line is '1';
       # if it is, this must be the beginning of the means list, and not an F1
       # measurement
        if line.split(',')[0] == '1':
            fields = line.split(',')
            break
        else:
            vm = process_measurement_line(line)
            Plt.measurements.append(vm)
            line = f.readline().strip()

    # now we're at the start of the means
    if not fields:  # it makes a difference whether we are coming here from a blank line, or from the first line of the means
        line = f.readline().strip()
        fields = line.split(',')

    # process the means
    while line != '':
        # print "Values for vowel class\t%s\t are %s." % (fields[0],
        # fields[1:])
        Plt.means[fields[0]] = fields[1:]
        line = f.readline().strip()
        fields = line.split(',')
    f.close()

    # perform check on number of measurements/tokens
    if len(Plt.measurements) != int(Plt.N):
        print "ERROR:  N's do not match for %s" % filename
        print "len(Plt.measurements) is %s; Plt.N is %s." % (len(Plt.measurements), Plt.N)
        return None
    else:
        return Plt


def split_stress_digit(phones):
    """separates the stress digit from the Arpabet code for vowels"""

    for p in phones:
        if p.label[-1:] in ['0', '1', '2']:
            p.arpa = p.label[:-1]
            p.stress = p.label[-1:]
        else:
            p.arpa = p.label
            p.stress = None
    return phones


def style2plotnik(stylecode, word):
    """converts single- or double-letter style codes to the corresponding Plotnik digits"""
    if stylecode not in STYLES:
# print "ERROR!  Style code %s of word % s is not an allowed option." % (stylecode, word)
# sys.exit()
        return stylecode
    else:
        return STYLES[stylecode]


def word2fname(word):
    """makes a unique filename out of token name???  (limited to 8 characters, count included as final) ???"""
    fname = word.replace('(', '')  # delete initial parenthesis
    fname = fname.replace(')', '')  # delete final parenthesis
    fname = fname.replace('-', '')  # delete dashes ???
    fname = re.sub(glide_regex, '', fname)
                   # bug fix if space between token & glide annotation is
                   # missing?
    fname = str.upper(fname)  # transform to upper case
    if len(fname) > 8:
        last = fname[-1]
        if last in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            fname = fname[0:7] + last
        else:
            fname = fname[0:8]
    return fname


def word2trans(word):
    """converts Plotnik word as originally entered (with parentheses and token number) into normal transcription (upper case)"""
    trans = word.replace('(', '')  # delete initial parenthesis
    trans = trans.replace(')', '')  # delete final parenthesis
    # the glide annotation, if it exists, is outside the count, so this must
    # be done first
    trans = re.sub(glide_regex, '', trans)
                   # bug fix if space between token & glide annotation is
                   # missing?
    trans = re.sub(count_regex, '', trans)
    trans = str.upper(trans)  # transform to upper case
    return trans
