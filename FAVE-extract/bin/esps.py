#
# !!! This is NOT the original esps.py file !!!                     ##
#
# Last modified by Ingrid Rosenfelder:  March 4, 2010                                ##
# - comments (all comments beginning with a double pound sign ("##"))                ##
# - docstrings for all classes and functions                                         ##
# -           ##
# -                                                        ##
#

import sys
import os
import re

# this file specifies the formatting used by fea_print to examine the .fb file
STYLE_FILE = './formant.sty'

espsExtensions = ['.f0', '.fb', '.fb.sig', '.hp', '.pole', '.ds']

pat1 = re.compile('  *')
pat2 = re.compile('^ ')


class Formant:

    def __init__(self):
        self.__times = []
        self.__formants = []
        self.__bandwidths = []
        self.__poles = []
        self.__pole_bandwidths = []
        self.__nx = None
        self.__dx = None
        self.__x1 = None

    def times(self):
        return self.__times

    def formants(self):
        return self.__formants

    def bandwidths(self):
        return self.__bandwidths

    def poles(self):
        return self.__poles

    def pole_bandwidths(self):
        return self.__pole_bandwidths

    def nx(self):
        return self.__nx

    def dx(self):
        return self.__dx

    def x1(self):
        return self.__x1

    def read(self, poleFile, fbFile):
        """ read formant tracking info from ESPS .fb file and get sampling and pole / bandwidth info from .pole file"""
        text = open(poleFile, 'rU')
        line = text.readline()
        while line.split(':')[0] != 'operation lpc_poles':
            line = text.readline()
        text.readline()
        self.__nx = int(text.readline().rstrip().split(' ')[1])
        self.__dx = 1 / float(text.readline().rstrip().split(' ')[1])
        self.__x1 = float(text.readline().rstrip().split(' ')[1])
        # this line contains the date of the measurement
        text.readline()
        for i in range(self.__nx):
            line = text.readline()
            # replace multiple spaces with a single space
            line = pat1.sub(' ', line)
            # delete the space at the beginning of the line
            line = pat2.sub('', line)
            values = line.strip().split(' ')
            n_poles = (int(values[0]) - 2) / 2
            P = [float(x) for x in values[3:3 + n_poles]]
            PB = [float(x) for x in values[3 + n_poles:]]
            self.__poles.append(P)
            self.__pole_bandwidths.append(PB)
        text.close()

        p = os.popen('fea_print ' + STYLE_FILE + ' ' + fbFile)
        lines = p.readlines()
        if len(lines) < self.__nx:
            print filename
            print "ERROR:  number of samples from .pole file (%d) not equal to output of fea_print (%s)" % (self.__nx, len(lines))
            sys.exit()
        for i in range(self.__nx):
            time = i * self.__dx + self.__x1
            F = []
            B = []
            fields = lines[i].rstrip('\n').split('\t')
            # for now, it's hardcoded into STYLE_FILE that we're asking ESPS to
            # extract three formants
            F.append(int(fields[0]))
            F.append(int(fields[1]))
            F.append(int(fields[2]))
            B.append(int(fields[3]))
            B.append(int(fields[4]))
            B.append(int(fields[5]))
            self.__times.append(time)
            self.__formants.append(F)
            self.__bandwidths.append(B)


class LPC:

    def __init__(self):
        self.__times = []
        self.__poles = []
        self.__bandwidths = []
        self.__nx = None
        self.__dx = None
        self.__x1 = None

    def times(self):
        return self.__times

    def poles(self):
        return self.__poles

    def bandwidths(self):
        return self.__bandwidths

    def nx(self):
        return self.__nx

    def dx(self):
        return self.__dx

    def x1(self):
        return self.__x1

    def read(self, filename):
        """ get sampling and pole / bandwidth info from .pole file"""
        text = open(filename, 'rU')
        line = text.readline()
        while line.split(':')[0] != 'operation lpc_poles':
            line = text.readline()
        text.readline()
        self.__nx = int(text.readline().rstrip().split(' ')[1])
        self.__dx = 1 / float(text.readline().rstrip().split(' ')[1])
        self.__x1 = float(text.readline().rstrip().split(' ')[1])
        # this line contains the date of the measurement
        text.readline()
        for i in range(self.__nx):
            # calculate the time stamp for this measurement
            time = i * self.__dx + self.__x1
            self.__times.append(time)

            line = text.readline()
            # replace multiple spaces with a single space
            line = pat1.sub(' ', line)
            # delete the space at the beginning of the line
            line = pat2.sub('', line)
            values = line.strip().split(' ')
            n_poles = (int(values[0]) - 2) / 2
            P = [float(x) for x in values[3:3 + n_poles]]
            PB = [float(x) for x in values[3 + n_poles:]]
            self.__poles.append(P)
            self.__bandwidths.append(PB)
        text.close()


def runFormant(wavFile):
    formantOptions = ''
    os.system('formant ' + formantOptions + wavFile)


def rmFormantFiles(fileStem):
    """deletes all files with ESPS extensions for a given file stem"""
    for ext in espsExtensions:
        if os.path.exists(fileStem + ext):
            os.remove(fileStem + ext)
