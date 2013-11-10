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
