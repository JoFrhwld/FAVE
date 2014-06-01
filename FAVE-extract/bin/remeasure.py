#import ast
import math
import numpy as np
import sys
import string

from mahalanobis import mahalanobis


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


def loadfile(file):
    """
    Loads an extractFormants file. Returns formatted list of lists.
    """
    f = open(file)
    sys.stdout.write(f.readline())
    f.readline()
    f.readline()
    #sys.stderr.write("Reading file...")
    lines = f.readlines()
    f.close()
    lines = [line.rstrip().split("\t") for line in lines]
    measurements = []
    for line in lines:
        vm = VowelMeasurement()
        vm.cd = line[vowelindex]
        vm.f1 = float(line[3])
        vm.f2 = float(line[4])
        if line[5] != "":
            vm.f3 = float(line[5])
        vm.b1 = float(line[6])
        vm.b2 = float(line[7])
        if line[8] != "":
            vm.b3 = float(line[8])
        vm.dur = float(line[12])
        vm.phone = line[0]
        vm.stress = line[1]
        vm.word = line[2]
        vm.t = line[9]
        vm.beg = line[10]
        vm.end = line[11]
        vm.poles = [[float(y) for y in x.rstrip(']').lstrip('[').split(',')]
                    for x in line[21].split('],[')]
        vm.bandwidths = [[float(y) for y in x.rstrip(']').lstrip('[').split(',')]
                         for x in line[22].split('],[')]
        measurements.append(vm)
    #sys.stderr.write("File read\n")
    return measurements


def createVowelDictionary(measurements):
    """
    Creates a dictionary of F1, F2, B1, B3 and Duration observations by vowel type.
    vowel index indicates the index in lines[x] which should be taken as identifying vowel categories.
    """
    vowels = {}
    #sys.stderr.write("Creating vowel dictionary...")

    for vm in measurements:
        if vm.cd in vowels:
#            vowels[vowel].append([F1, F2,F3,  B1, B2, B3, Dur])
            vowels[vm.cd].append(
                [vm.f1, vm.f2,  math.log(vm.b1), math.log(vm.b2), math.log(vm.dur)])
        else:
#            vowels[vowel] = [[F1, F2, F3, B1, B2, B3, Dur]]
            vowels[vm.cd] = [
                [vm.f1, vm.f2,  math.log(vm.b1), math.log(vm.b2), math.log(vm.dur)]]

    #sys.stderr.write("Vowel dictionary created\n")
    return vowels


def excludeOutliers(vowels, vowelMeans, vowelCovs):
    """
    Finds outliers and excludes them.
    """
    # sys.stderr.write("Excluding outlying vowels...")
    outvowels = {}
    for vowel in vowels:
        if vowel in vowelCovs:
            ntokens = len(vowels[vowel])
            if ntokens >= 10:
                outlie = 4.75
                outvowels[vowel] = pruneVowels(
                    vowels, vowel, vowelMeans, vowelCovs, outlie)
            else:
                outvowels[vowel] = vowels[vowel]
        else:
            outvowels[vowel] = vowels[vowel]
    # sys.stderr.write("excluded.\n")
    return(outvowels)


def pruneVowels(vowels, vowel, vowelMeans, vowelCovs, outlie):
    """
    Tries to prune outlier vowels, making sure enough tokens are left to calculate mahalanobis distance.
    """
    enough = False

    while not enough:
        outtokens = []
        for token in vowels[vowel]:
            x = np.array(token)
            dist = mahalanobis(x, vowelMeans[vowel], vowelCovs[vowel])
            if dist ** 2 <= outlie:
                outtokens.append(token)
        if len(outtokens) >= 10:
            enough = True
        else:
            outlie = outlie + 0.5

    return(outtokens)


def calculateVowelMeans(vowels):
    """
    calculates [means] and [covariance matrices] for each vowel class.
    It returns these as numpy arrays in dictionaries indexed by the vowel class.
    """
    #sys.stderr.write("Calculating vowel means...")
    vowelMeans = {}
    vowelCovs = {}
    for vowel in vowels:
        vF1 = np.array([F1 for [F1, F2, B1, B2, Dur] in vowels[vowel]])
        vF2 = np.array([F2 for [F1, F2, B1, B2, Dur] in vowels[vowel]])
        vB1 = np.array([B1 for [F1, F2, B1, B2, Dur] in vowels[vowel]])
        vB2 = np.array([B2 for [F1, F2, B1, B2, Dur] in vowels[vowel]])
        vDur = np.array([Dur for [F1, F2, B1, B2, Dur] in vowels[vowel]])

        vowelMeans[vowel] = np.array(
            [vF1.mean(), vF2.mean(), vB1.mean(), vB2.mean(), vDur.mean()])
        if vF1.shape[0] >= 7:
            vowel_cov = np.cov(np.vstack((vF1, vF2, vB1, vB2, vDur)))
            if np.linalg.det(vowel_cov) != 0:
                vowelCovs[vowel] = np.linalg.inv(vowel_cov)
    #sys.stderr.write("Vowel means calculated\n")
    return vowelMeans, vowelCovs


def repredictF1F2(measurements, vowelMeans, vowelCovs, vowels):
    """
    Predicts F1 and F2 from the speaker's own vowel distributions based on the mahalanobis distance.
    """
    # print "\nREMEASURING..."
    remeasurements = []
    for vm in measurements:

        valuesList = []
        distanceList = []
        nFormantsList = []
        vowel = vm.cd

        # if no remeasurement takes place, the new winner index will be automatically zero (see the three cases listed below)
        # but we actually want to keep the old values for the formant tracks
        keepOldTracks = True

        for i in range(len(vm.poles)):
            if len(vm.poles[i]) >= 2:
                F1 = vm.poles[i][0]
                F2 = vm.poles[i][1]
                if len(vm.poles[i]) >= 3 and vm.poles[i][2]:  # could be "None"
                    F3 = vm.poles[i][2]
                else:
                    F3 = "NA"
                B1 = math.log(vm.bandwidths[i][0])
                B2 = math.log(vm.bandwidths[i][1])
                if len(vm.bandwidths[i]) >= 3 and vm.poles[i][2]:
                    B3 = vm.bandwidths[i][2]
                else:
                    B3 = "NA"

                ##nFormants = len(vm.poles[i])
                lDur = math.log(vm.dur)
                values = [F1, F2, B1, B2, lDur]
                outvalues = [F1, F2, F3, B1, B2, B3, lDur]

                x = np.array(values)

                # If there is only one member of a vowel category,
                # the covariance matrix will be filled with NAs
                # sys.stderr.write(vowel+"\n")
                if vowel in vowelCovs:
                    # if no re-measurement is to take place for one of the three reasons below, the list of candidate measurements and nFormants
                    # will be filled with four identical copies of the original measurement, all with a distance of zero
                    # so that the original measurement is guaranteed to be
                    # re-selected
                    if np.isnan(vowelCovs[vowel][0, 0]):
                        valuesList.append(
                            [float(vm.f1), float(vm.f2), vm.f3, math.log(float(vm.b1)), math.log(float(vm.b2)), vm.b3, lDur])
                        distanceList.append(0)
                        nFormantsList.append(vm.nFormants)
                    elif len(vowels[vowel]) < 7:
                        valuesList.append(
                            [float(vm.f1), float(vm.f2), vm.f3, math.log(float(vm.b1)), math.log(float(vm.b2)), vm.b3, lDur])
                        distanceList.append(0)
                        nFormantsList.append(vm.nFormants)
                    # "real" re-measurement
                    else:
                        dist = mahalanobis(
                            x, vowelMeans[vowel], vowelCovs[vowel])
                        valuesList.append(outvalues)
                        distanceList.append(dist)
                        nFormantsList.append(
                            i + 3)  # these are the formant setting used, not the actual number of formants returned
                        keepOldTracks = False
                else:
                    valuesList.append(
                        [float(vm.f1), float(vm.f2), vm.f3, math.log(float(vm.b1)), math.log(float(vm.b2)), vm.b3, lDur])
                    distanceList.append(0)
                    nFormantsList.append(i + 3)

        winnerIndex = distanceList.index(min(distanceList))
        dist = repr(min(distanceList))
        bestValues = valuesList[winnerIndex]
        bestnFormants = nFormantsList[winnerIndex]
# if bestnFormants != vm.nFormants:
# print "\tVowel %s in word %s was originally measured with nFormants = %s; now measured with nFormants = %s!" % (vm.phone, vm.word, vm.nFormants, bestnFormants)
# print "\told formant tracks:\n\t\t%s" % vm.tracks
# print "\tnew formant tracks:\n\t\t%s\n" % vm.all_tracks[winnerIndex]

        # change formants and bandwidths to new values
        vm.f1 = round(bestValues[0], 1)
        vm.f2 = round(bestValues[1], 1)
        if bestValues[2] != "NA" and bestValues[2] != None:
            vm.f3 = round(bestValues[2], 1)
        else:
            vm.f3 = ''
        vm.b1 = round(math.exp(bestValues[3]), 1)
        vm.b2 = round(math.exp(bestValues[4]), 1)
        if bestValues[5] != "NA" and bestValues[5] != None:
            try:
                vm.b3 = round(bestValues[5], 1)
            except OverflowError:
                vm.b3 = ''
        else:
            vm.b3 = ''
        vm.nFormants = bestnFormants
        # change formant tracks to new values as well
        if not keepOldTracks:
            vm.tracks = vm.all_tracks[winnerIndex]
            vm.winner_poles = vm.all_poles[winnerIndex]
            vm.winner_bandwidths = vm.all_bandwidths[winnerIndex]
        remeasurements.append(vm)

    return remeasurements


def output(remeasurements):
    """writes measurements to file according to selected output format"""
    fw = open("remeasure.txt", 'w')
    # header
    fw.write(
        '\t'.join(['vowel', 'stress', 'word', 'F1', 'F2', 'F3', 'B1', 'B2', 'B3', 't', 'beg', 'end',
                   'dur', 'cd', 'fm', 'fp', 'fv', 'ps', 'fs', 'style', 'glide', 'nFormants', 'poles', 'bandwidths']))
    fw.write('\n')
    for vm in measurements:
        fw.write(
            '\t'.join([vm.phone, str(vm.stress), vm.word, str(vm.f1), str(vm.f2)]))
                 # vowel (ARPABET coding), stress, word, F1, F2
        fw.write('\t')
        if vm.f3:
            fw.write(str(vm.f3))  # F3 (if present)
        fw.write('\t')
        fw.write('\t'.join([str(vm.b1), str(vm.b2)]))  # B1, B2
        fw.write('\t')
        if vm.b3:
            fw.write(str(vm.b3))  # B3 (if present)
        fw.write('\t')
        fw.write(
            '\t'.join([str(vm.t), str(vm.beg), str(vm.end), str(vm.dur), vm.cd, vm.fm, vm.fp, vm.fv, vm.ps, vm.fs, vm.style, vm.glide]))
        fw.write('\t')
                 # time of measurement, beginning and end of phone, duration,
                 # Plotnik environment codes, style coding, glide coding
        if vm.nFormants:
            fw.write(str(vm.nFormants))
                     # nFormants selected (if Mahalanobis method)
        fw.write('\t')
        fw.write(
            '\t'.join([','.join([str(p) for p in vm.poles]), ','.join([str(b) for b in vm.bandwidths])]))
                 # candidate poles and bandwidths (at point of measurement)
        fw.write('\n')
    fw.close()


def remeasure(measurements):
    vowels = createVowelDictionary(measurements)
    vowelMeans, vowelCovs = calculateVowelMeans(vowels)
    invowels = excludeOutliers(vowels, vowelMeans, vowelCovs)
    vowelMeans, vowelCovs = calculateVowelMeans(invowels)
    remeasurements = repredictF1F2(measurements, vowelMeans, vowelCovs, vowels)
    return remeasurements

# Main Program Starts Here
# Define some constants
#file = "/Users/joseffruehwald/Documents/Classes/Fall_10/misc/FAAV/extractFormants_modified/PH06-2-1-AB-Jean.formants"
if __name__ == '__main__':
    file = sys.argv[1]
    vowelindex = 13
    measurements = loadfile(file)
    remeasurements = remeasure(measurements)
    output(remeasurements)
