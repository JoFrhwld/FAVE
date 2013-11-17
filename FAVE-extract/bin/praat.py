#
# !!! This is NOT the original praat.py file !!!                    ##
#
# Last modified by Ingrid Rosenfelder:  February 2, 2012                             ##
# - comments (all comments beginning with a double pound sign ("##"))                ##
# - docstrings for all classes and functions                                         ##
# - read() methods for TextGrid can read both long and short file formats            ##
# - formant frames no longer need to have a minimum of x formants (formerly three)   ##
# (smoothing routine in extractFormants.py demands equal spacing between frames)   ##
# - added Intensity class                                                            ##
# - round all times to three digits (i.e. ms)                                        ##
# - improved reading of long TextGrid format                                         ##
#


class Formant:

    """represents a formant contour as a series of frames"""

    def __init__(self, name=None):
        self.__times = []  # list of measurement times (frames)
        self.__intensities = []
            # list of intensities (maximum intensity in each frame)
        self.__formants = []
            # list of formants frequencies (F1-F3, for each frame)
        self.__bandwidths = []
            # list of bandwidths (for each formant F1-F3, for each frame)
                                      # !!! CHANGED:  all above lists no longer include frames with only
                                      # a minimum of 2 formant measurements
                                      # !!!
        self.__xmin = None  # start time (in seconds)
        self.__xmax = None  # end time (in seconds)
        self.__nx = None  # number of frames
        self.__dx = None  # time step = frame duration (in seconds)
        self.__x1 = None  # start time of first frame (in seconds)
        self.__maxFormants = None  # maximum number of formants in a frame

    def n(self):
        """returns the number of frames"""
        return self.__nx

    def xmin(self):
        """returns start time (in seconds)"""
        return self.__xmin

    def xmax(self):
        """returns end time (in seconds)"""
        return self.__xmax

    def times(self):
        """returns list of measurement times (frames)"""
        return self.__times

    def intensities(self):
        """returns list of intensities (maximum intensity in each frame)"""
        return self.__intensities

    def formants(self):
        """returns list of formant listings (F1-F3, for each frame)"""
        return self.__formants

    def bandwidths(self):
        """returns a list of formant bandwidths (for each formant F1-F3, for each frame)"""
        return self.__bandwidths

    def read(self, file):
        """reads Formant from Praat .Formant file (either short or long file format)"""
        text = open(file, 'rU')
        text.readline()  # header
        text.readline()
        text.readline()
        # short or long Formant format?
        line = text.readline().rstrip().split()  # read fields in next line
        if len(line) == 3 and line[0] == "xmin":  # line reads "xmin = xxx.xxxxx"
            format = "long"
        elif len(line) == 1 and line[0] != '':  # line reads "xxx.xxxxx"
            format = "short"
        else:
            print "WARNING!!!  Unknown format for Formant file!"

        if format == "short":  # SHORT FORMANT FORMAT
            self.__xmin = round(float(line[0]), 3)  # start time
            self.__xmax = round(float(text.readline().rstrip()), 3)  # end time
            self.__nx = int(text.readline().rstrip())  # number of frames
            self.__dx = round(
                float(text.readline().rstrip()), 3)  # frame duration
            self.__x1 = round(
                float(text.readline().rstrip()), 3)  # time of first frame
            self.__maxFormants = int(
                text.readline().rstrip())  # maximum number of formants

            for i in range(self.__nx):  # for each frame:
                time = round((i * self.__dx + self.__x1), 3)
                intensity = float(text.readline().rstrip())
                nFormants = int(text.readline().rstrip())
                F = []
                B = []
                for j in range(nFormants):
                    F.append(float(text.readline().rstrip()))
                    B.append(float(text.readline().rstrip()))
                # CHANGED
                # force at least 3 formants to be returned for each measurment,
                # if Praat didn't find at least three, then we'll disregard this measurement
                # if nFormants < 2:
                #  continue
                self.__times.append(time)
                self.__intensities.append(intensity)
                self.__formants.append(F)
                self.__bandwidths.append(B)

        elif format == "long":  # LONG FORMANT FORMAT
            self.__xmin = round(float(line[2]), 3)  # start time
            self.__xmax = round(
                float(text.readline().rstrip().split()[2]), 3)  # end time
            self.__nx = int(
                text.readline().rstrip().split()[2])  # number of frames
            self.__dx = round(
                float(text.readline().rstrip().split()[2]), 3)  # frame duration
            self.__x1 = round(
                float(text.readline().rstrip().split()[2]), 3)  # time of first frame
            self.__maxFormants = int(
                text.readline().rstrip().split()[2])  # maximum number of formants

            text.readline()  # "frame[]:"
            for i in range(self.__nx):  # for each frame:
                text.readline()  # "frame[i]:"
                time = round((i * self.__dx + self.__x1), 3)
                intensity = float(text.readline().rstrip().split()[2])
                nFormants = int(text.readline().rstrip().split()[2])
                F = []
                B = []
                text.readline()  # "formant[]:"
                for j in range(nFormants):
                    text.readline()  # "formant[i]:"
                    F.append(float(text.readline().rstrip().split()[2]))
                    B.append(float(text.readline().rstrip().split()[2]))
                # see above...
                # force at least 3 formants to be returned for each measurment,
                # if Praat didn't find at least three, then we'll disregard this measurement
                # if nFormants < 2:
                #  continue
                self.__times.append(time)
                self.__intensities.append(intensity)
                self.__formants.append(F)
                self.__bandwidths.append(B)

        # update self.__nx
        self.__nx = len(self.__formants)
        text.close()


class LPC:

    """represents a Praat LPC (linear predictive coding) object"""

    def __init__(self):
        self.__times = []
        self.__intensities = []
        self.__poles = []
        self.__bandwidths = []
        self.__xmin = None
        self.__xmax = None
        self.__nx = None
        self.__dx = None
        self.__x1 = None
        self.__maxFormants = None

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

    def read(self, file):
        """reads LPC object from Praat .LPC file (saved as a short text file) """
        text = open(file, 'rU')
        text.readline()  # header
        text.readline()
        text.readline()
        self.__xmin = float(text.readline().rstrip())
        self.__xmax = float(text.readline().rstrip())
        self.__nx = int(text.readline().rstrip())
        self.__dx = float(text.readline().rstrip())
        self.__x1 = float(text.readline().rstrip())
        self.__maxFormants = int(text.readline().rstrip())

        for i in range(self.__nx):
            time = i * self.__dx + self.__x1
            intensity = float(text.readline().rstrip())
            nFormants = int(text.readline().rstrip())
            F = []
            B = []
            for j in range(nFormants):
                F.append(float(text.readline().rstrip()))
                B.append(float(text.readline().rstrip()))
            # force at least 3 formants to be returned for each measurment, if
            # Praat didn't find at least three, then we'll disregard this
            # measurement
            if nFormants < 3:
                continue
            self.__times.append(time)
            self.__intensities.append(intensity)
            self.__poles.append(F)
            self.__bandwidths.append(B)

        text.close()


class MFCC:

    """represents a Praat MFCC (mel frequency cepstral coefficients) object"""

    def __init__(self):
        self.__times = []
        self.__mfccs = []
        self.__xmin = None
        self.__xmax = None
        self.__nx = None
        self.__dx = None
        self.__x1 = None
        self.__fmin = None
        self.__fmin = None
        self.__maximumNumberOfCoefficients = None

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def nx(self):
        return self.__nx

    def dx(self):
        return self.__dx

    def x1(self):
        return self.__x1

    def fmin(self):
        return self.__fmin

    def fmax(self):
        return self.__fmax

    def times(self):
        return self.__times

    def mfccs(self):
        return self.__mfccs

    def read(self, file):
        """reads MFCC object from Praat .MFCC file (saved as a short text file) """
        text = open(file, 'rU')
        text.readline()  # header
        text.readline()
        text.readline()
        self.__xmin = float(text.readline().rstrip())
        self.__xmax = float(text.readline().rstrip())
        self.__nx = int(text.readline().rstrip())
        self.__dx = float(text.readline().rstrip())
        self.__x1 = float(text.readline().rstrip())
        self.__fmin = float(text.readline().rstrip())
        self.__fmax = float(text.readline().rstrip())
        self.__maximumNumberOfCoefficients = int(text.readline().rstrip())

        for i in range(self.__nx):
            time = i * self.__dx + self.__x1
            nCoefficients = int(text.readline().rstrip())
            M = []
            # the first one is c0, the energy coefficient
            M.append(float(text.readline().rstrip()))
            for j in range(nCoefficients):
                M.append(float(text.readline().rstrip()))
            self.__times.append(time)
            self.__mfccs.append(M)

        text.close()


class Intensity:

    """represents an intensity contour"""

    def __init__(self):
        self.__xmin = None
        self.__xmax = None
        self.__n = None
        self.__dx = None
        self.__x1 = None
        self.__times = []
        self.__intensities = []

    def __str__(self):
        return '<Intensity object with %i frames>' % self.__n

    def __iter__(self):
        return iter(self.__intensities)

    def len(self):
        return self.__n

    def __getitem__(self, i):
        """returns the (i+1)th intensity frame"""
        return self.__intensities[i]

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def times(self):
        return self.__times

    def intensities(self):
        return self.__intensities

    def times(self):
        return self.__times

    def change_offset(self, offset):
        self.__xmin += offset
        self.__xmax += offset
        self.__x1 += offset
        self.__times = [t + offset for t in self.__times]

    def read(self, filename):
        """reads an intensity object from a (short or long) text file"""
        text = open(filename, 'rU')
        text.readline()  # "File type = ..."
        text.readline()  # "Object class = ..."
        text.readline()
        # short or long Formant format?
        line = text.readline().rstrip().split()  # read fields in next line
        if len(line) == 3 and line[0] == "xmin":  # line reads "xmin = xxx.xxxxx"
            format = "long"
        elif len(line) == 1 and line[0] != '':  # line reads "xxx.xxxxx"
            format = "short"
        else:
            print "WARNING!!!  Unknown format for Intensity file!"

        if format == "short":  # SHORT FORMAT
            self.__xmin = round(float(line[0]), 3)  # start time (xmin)
            self.__xmax = round(
                float(text.readline().rstrip()), 3)  # end time (xmax)
            self.__n = int(text.readline().rstrip())  # number of frames (nx)
            self.__dx = round(
                float(text.readline().rstrip()), 3)  # frame duration (dx)
            self.__x1 = round(
                float(text.readline().rstrip()), 3)  # time of first frame (x1)
            text.readline()  # (ymin)
            text.readline()  # (ymax)
            text.readline()  # (ny)
            text.readline()  # (dy)
            text.readline()  # (y1)
            for i in range(self.__n):  # for each frame:
                time = round((i * self.__dx + self.__x1), 3)
                intensity = float(text.readline().rstrip())
                self.__times.append(time)
                self.__intensities.append(intensity)

        elif format == "long":  # LONG FORMAT
            self.__xmin = round(float(line[2]), 3)  # start time (xmin)
            self.__xmax = round(
                float(text.readline().rstrip().split()[2]), 3)  # end time (xmax)
            self.__n = int(
                text.readline().rstrip().split()[2])  # number of frames (nx)
            self.__dx = round(
                float(text.readline().rstrip().split()[2]), 3)  # frame duration (dx)
            self.__x1 = round(
                float(text.readline().rstrip().split()[2]), 3)  # time of first frame (x1)
            text.readline()  # (ymin)
            text.readline()  # (ymax)
            text.readline()  # (ny)
            text.readline()  # (dy)
            text.readline()  # (y1)
            text.readline()  # "z [] []: "
            text.readline()  # "z [1]: "
            for i in range(self.__nx):  # for each frame:
                time = round((i * self.__dx + self.__x1), 3)
                intensity = float(text.readline().rstrip().split(' = ')[1])
                self.__times.append(time)
                self.__intensities.append(intensity)

        # update self.__n
        self.__nx = len(self.__intensities)
        text.close()


class TextGrid:

    """represents a Praat TextGrid"""

    def __init__(self, name=''):
        self.__tiers = []
        self.__n = len(self.__tiers)
        self.__xmin = 0
        self.__xmax = 0
        self.__name = name

    def __str__(self):
        return '<TextGrid with %d tiers>' % self.__n

    def __iter__(self):
        return iter(self.__tiers)

    def __len__(self):
        return self.__n

    def __getitem__(self, i):
        """ return the (i+1)th tier """
        return self.__tiers[i]

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def name(self):
        return self.__name

    def append(self, tier):
        self.__tiers.append(tier)
        self.__xmax = max(tier.xmax(), self.__xmax)
        self.__xmin = min(tier.xmin(), self.__xmin)
        self.__n = len(self.__tiers)

    def change_offset(self, offset):
        self.__xmin += offset
        self.__xmax += offset
        for tier in self.__tiers:
            tier.change_offset(offset)

    def change_times(self, beg, end):
        self.__xmin = beg
        self.__xmax = end

    def read(self, filename):
        """reads TextGrid from Praat .TextGrid file (long or short format)"""
        text = open(filename, 'rU')
        text.readline()
                      # header                            ## line reads 'File
                      # type = "ooTextFile"'
        text.readline()  # line reads 'Object class = "TextGrid"'
        text.readline()  # blank line
        # short or long Formant format?
        line = text.readline().strip().split()  # read fields in next line
        if len(line) == 3 and line[0] == "xmin":  # line reads "xmin = xxx.xxxxx"
            format = "long"
        elif len(line) == 1 and line[0] != '':  # line reads "xxx.xxxxx"
            format = "short"
        else:
            print "WARNING!!!  Unknown format for Formant file!"

        if format == "short":  # SHORT TEXTGRID FORMAT
            self.__xmin = round(
                float(line[0]), 3)  # round to 3 digits; line reads "xxx.xxxxx"
            self.__xmax = round(
                float(text.readline().rstrip()), 3)  # line reads "xxx.xxxxx"
            text.readline()  # line reads "<exists>" (tiers exist)
            m = int(text.readline().rstrip())
                    # line reads "x" (number of tiers)
            for i in range(m):  # loop over tiers
                # [1:-1] strips off the quote characters surrounding all labels
                if text.readline().strip()[1:-1] == 'IntervalTier':  # line reads '"IntervalTier"'
                    inam = text.readline().rstrip()[
                        1:-1]  # line reads '"abcdefg"' (tier label)
                    imin = round(float(text.readline().strip()), 3)
                                 # line reads "xxx.xxxxx" (beginning of tier)
                    imax = round(float(text.readline().strip()), 3)
                                 # line reads "xxx.xxxxx" (end of tier)
                    itier = IntervalTier(inam, imin, imax)
                    n = int(text.readline().rstrip())
                            # line reads "xxxxx" (number of intervals in tier)
                    for j in range(n):
                        jmin = round(float(text.readline().strip()), 3)
                                     # line reads "xxx.xxxxx" (beginning of
                                     # interval)
                        jmax = round(float(text.readline().strip()), 3)
                                     # line reads "xxx.xxxxx" (end of interval)
                        jmrk = text.readline().strip()[
                            1:-1]  # line reads '"abcdefg"' (interval label)
                        itier.append(Interval(jmin, jmax, jmrk))
                    self.append(itier)  # automatically updates self.__n
                else:  # pointTier
                    inam = text.readline().rstrip()[1:-1]
                    imin = round(float(text.readline().rstrip()), 3)
                    imax = round(float(text.readline().rstrip()), 3)
                    itier = PointTier(inam, imin, imax)
                    n = int(text.readline().rstrip())
                    for j in range(n):
                        jtim = round(float(text.readline().rstrip()), 3)
                        jmrk = text.readline().rstrip()[1:-1]
                        itier.append(Point(jtim, jmrk))
                    self.append(itier)
            if self.__n != m:
                print "In TextGrid.IntervalTier.read:  Error in number of tiers!"
            text.close()
        elif format == "long":  # LONG TEXTGRID FORMAT
            self.__xmin = round(
                float(line[2]), 3)  # line reads "xmin = xxx.xxxxx"
            self.__xmax = round(
                float(text.readline().strip().split(' = ')[1]), 3)  # line reads "xmax = xxx.xxxxx"
            text.readline()  # line reads "tiers? <exists>"
            m = int(text.readline().strip().split(
                ' = ')[1])  # line reads "size = x"
            text.readline()  # line reads "item []:"
            for i in range(m):  # loop over tiers
                text.readline()  # line reads "item [x]:"
                if text.readline().rstrip().split()[2] == '"IntervalTier"':  # line reads "class = 'IntervalTier"'
                    inam = text.readline().strip().split('=')[
                        1].strip()[1:-1]  # line reads 'name = "xyz"'
                    imin = round(
                        float(text.readline().strip().split('=')[1].strip()), 3)  # line reads "xmin = xxx.xxxxx"
                    imax = round(
                        float(text.readline().strip().split('=')[1].strip()), 3)  # line reads "xmax = xxx.xxxxx"
                    itier = IntervalTier(inam, imin, imax)
                    n = int(text.readline().strip().split('=')[
                            1].strip())  # line reads "intervals: size = xxxxx"
                    for j in range(n):
                        text.readline()
                                      # header junk
                                      # ## line reads "intervals [x]:"
                        jmin = round(
                            float(text.readline().strip().split('=')[1].strip()), 3)  # line reads "xmin = xxx.xxxxx"
                        jmax = round(
                            float(text.readline().strip().split('=')[1].strip()), 3)  # line reads "xmax = xxx.xxxxx"
                        jmrk = text.readline().strip().split('=')[
                            1].strip()[1:-1]  # line reads 'text = "xyz"'
                        itier.append(Interval(jmin, jmax, jmrk))
                    self.append(itier)  # automatically updates self.__n
                else:  # pointTier
                    inam = text.readline().strip().split('=')[1].strip()[1:-1]
                    imin = round(
                        float(text.readline().strip().split('=')[1].strip()), 3)
                    imax = round(
                        float(text.readline().strip().split('=')[1].strip()), 3)
                    itier = PointTier(inam, imin, imax)
                    n = int(text.readline().strip().split('=')[1].strip())
                    for j in range(n):
                        text.readline()  # header junk
                        jtim = round(
                            float(text.readline().strip().split('=')[1].strip()), 3)
                        jmrk = text.readline().strip().split(
                            '=')[1].strip()[1:-1]
                        itier.append(Point(jtim, jmrk))
                    self.append(itier)
            if self.__n != m:
                print "In TextGrid.IntervalTier.read:  Error in number of tiers!"
            text.close()

    def write(self, text):
        """ write TextGrid into a text file that Praat can read """
        text = open(text, 'w')
        text.write('File type = "ooTextFile"\n')
        text.write('Object class = "TextGrid"\n\n')
        text.write('xmin = %f\n' % self.__xmin)
        text.write('xmax = %f\n' % self.__xmax)
        text.write('tiers? <exists>\n')
        text.write('size = %d\n' % self.__n)
        text.write('item []:\n')
        for (tier, n) in zip(self.__tiers, range(1, self.__n + 1)):
            text.write('\titem [%d]:\n' % n)
            if tier.__class__ == IntervalTier:
                text.write('\t\tclass = "IntervalTier"\n')
                text.write('\t\tname = "%s"\n' % tier.name())
                text.write('\t\txmin = %f\n' % tier.xmin())
                text.write('\t\txmax = %f\n' % tier.xmax())
                text.write('\t\tintervals: size = %d\n' % len(tier))
                for (interval, o) in zip(tier, range(1, len(tier) + 1)):
                    text.write('\t\t\tintervals [%d]:\n' % o)
                    text.write('\t\t\t\txmin = %f\n' % interval.xmin())
                    text.write('\t\t\t\txmax = %f\n' % interval.xmax())
                    text.write('\t\t\t\ttext = "%s"\n' % interval.mark())
            else:  # PointTier
                text.write('\t\tclass = "TextTier"\n')
                text.write('\t\tname = "%s"\n' % tier.name())
                text.write('\t\txmin = %f\n' % tier.xmin())
                text.write('\t\txmax = %f\n' % tier.xmax())
                text.write('\t\tpoints: size = %d\n' % len(tier))
                for (point, o) in zip(tier, range(1, len(tier) + 1)):
                    text.write('\t\t\tpoints [%d]:\n' % o)
                    text.write('\t\t\t\ttime = %f\n' % point.time())
                    text.write('\t\t\t\tmark = "%s"\n' % point.mark())
        text.close()


class IntervalTier:

    """represents a Praat IntervalTier"""

    def __init__(self, name='', xmin=0, xmax=0):
        self.__intervals = []
        self.__n = len(self.__intervals)
        self.__name = name
        self.__xmin = xmin
        self.__xmax = xmax

    def __str__(self):
        return '<IntervalTier "%s" with %d intervals>' % (self.__name, self.__n)

    def __iter__(self):
        return iter(self.__intervals)

    def __len__(self):
        return self.__n

    def __getitem__(self, i):
        """returns the (i+1)th interval"""
        return self.__intervals[i]

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def name(self):
        return self.__name

    def append(self, interval):
        self.__intervals.append(interval)
        self.__xmax = max(interval.xmax(), self.__xmax)  # changed
        self.__xmin = min(interval.xmin(), self.__xmin)  # added
        self.__n = len(self.__intervals)  # changed to "automatic update"

    def read(self, file):
        text = open(file, 'r')
        text.readline()  # header junk
        text.readline()
        text.readline()
        self.__xmin = float(text.readline().rstrip().split()[2])
        self.__xmax = float(text.readline().rstrip().split()[2])
        m = int(text.readline().rstrip().split()[3])
        for i in range(m):
            text.readline().rstrip()  # header
            imin = float(text.readline().rstrip().split()[2])
            imax = float(text.readline().rstrip().split()[2])
            imrk = text.readline().rstrip().split()[2].replace('"', '')  # txt
            self.__intervals.append(Interval(imin, imax, imrk))
        text.close()
        self.__n = len(self.__intervals)

    def write(self, file):
        text = open(file, 'w')
        text.write('File type = "ooTextFile"\n')
        text.write('Object class = "IntervalTier"\n\n')
        text.write('xmin = %f\n' % self.__xmin)
        text.write('xmax = %f\n' % self.__xmax)
        text.write('intervals: size = %d\n' % self.__n)
        for (interval, n) in zip(self.__intervals, range(1, self.__n + 1)):
            text.write('intervals [%d]:\n' % n)
            text.write('\txmin = %f\n' % interval.xmin())
            text.write('\txmax = %f\n' % interval.xmax())
            text.write('\ttext = "%s"\n' % interval.mark())
        text.close()

    def rename(self, newname):
        """assigns new name to tier"""
        self.__name = newname

    def sort_intervals(self, par="xmin"):
        """sorts intervals according to given parameter values.  Parameter can be xmin (default), xmax, or text."""
        # function generating key used for sorting
        if par == "xmin":
            def f(i):
                return i.xmin()
        elif par == "xmax":
            def f(i):
                return i.xmax()
        elif par == "text":
            def f(i):
                return i.mark()
        else:
            sys.stderr.write("Invalid parameter for function sort_intervals.")
        self.__intervals.sort(key=f)

    def extend(self, newmin, newmax):
        # check that this is really an expansion
        if newmin > self.__xmin:
            print "Error!  New minimum of tier %f exceeds old minimum %f." % (newmin, self.__xmin)
            sys.exit()
        if newmax < self.__xmax:
            print "Error!  New maximum of tier %f is less than old maximum %f." % (newmax, self.__xmax)
            sys.exit()
        # add new intervals at beginning and end
        self.sort_intervals()
        if newmin != self.__intervals[0].xmin():
            self.__intervals.append(
                Interval(newmin, self.__intervals[0].xmin(), "sp"))
        self.sort_intervals()
        if newmax != self.__intervals[-1].xmax():
            self.__intervals.append(
                Interval(self.__intervals[-1].xmax(), newmax, "sp"))
        # update number of intervals
        self.__n = len(self.__intervals)
        # set new global maxima
        self.__xmin = newmin
        self.__xmax = newmax

    def tidyup(self):
        """inserts empty intervals in the gaps between transcription intervals"""
        self.sort_intervals()
        z = 0
        end = len(self.__intervals) - 1
        overlaps = []
        while z < end:  # (only go up to second-to-last interval)
            i = self.__intervals[z]
            if i.xmax() != self.__intervals[z + 1].xmin():
                # insert empty interval if xmax of interval and xmin of
                # following interval do not coincide
                if i.xmax() < self.__intervals[z + 1].xmin():
                    self.__intervals.append(
                        Interval(i.xmax(), self.__intervals[z + 1].xmin(), "sp"))
                    print "tidyup:  Added new interval %f:%f to tier %s." % (i.xmax(), self.__intervals[z + 1].xmin(), self.__name)
                    self.__n = len(self.__intervals)
                    self.sort_intervals()
                    # update iteration range
                    end = len(self.__intervals) - 1
                else:  # overlapping interval boundaries
                    overlaps.append((i, self.__intervals[z + 1], self.__name))
                    print "WARNING!!!  Overlapping intervals!!!"
                    print "%s and %s on tier %s." % (i, self.__intervals[z + 1], self.__name)
            z += 1
        return overlaps

    def change_offset(self, offset):
        self.__xmin += offset
        self.__xmax += offset
        for i in self.__intervals:
            i.change_offset(offset)


class PointTier:

    """represents a Praat PointTier"""

    def __init__(self, name='', xmin=0, xmax=0):
        self.__name = name
        self.__xmin = xmin
        self.__xmax = xmax
        self.__points = []
        self.__n = len(self.__points)

    def __str__(self):
        return '<PointTier "%s" with %d points>' % (self.__name, self.__n)

    def __iter__(self):
        return iter(self.__points)

    def __len__(self):
        return self.__n

    def __getitem__(self, i):
        """returns the (i+1)th point"""
        return self.__points[i]

    def name(self):
        return self.__name

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def append(self, point):
        self.__points.append(point)
        self.__xmax = max(self.__xmax, point.time())
        self.__xmin = min(self.__xmin, point.time())
        self.__n = len(self.__points)

    def read(self, file):
        text = open(file, 'r')
        text.readline()  # header junk
        text.readline()
        text.readline()
        self.__xmin = float(text.readline().rstrip().split()[2])
        self.__xmax = float(text.readline().rstrip().split()[2])
        self.__n = int(text.readline().rstrip().split()[3])
        for i in range(self.__n):
            text.readline().rstrip()  # header
            itim = float(text.readline().rstrip().split()[2])
            imrk = text.readline().rstrip().split()[2].replace('"', '')  # txt
            self.__points.append(Point(imrk, itim))
        text.close()

    def write(self, file):
        text = open(file, 'w')
        text.write('File type = "ooTextFile"\n')
        text.write('Object class = "TextTier"\n\n')
        text.write('xmin = %f\n' % self.__xmin)
        text.write('xmax = %f\n' % self.__xmax)
        text.write('points: size = %d\n' % self.__n)
        for (point, n) in zip(self.__points, range(1, self.__n + 1)):
            text.write('points [%d]:\n' % n)
            text.write('\ttime = %f\n' % point.time())
            text.write('\tmark = "%s"\n' % point.mark())
        text.close()


class Interval:

    """represents an Interval"""

    def __init__(self, xmin=0, xmax=0, mark=''):
        self.__xmin = xmin
        self.__xmax = xmax
        self.__mark = mark

    def __str__(self):
        return '<Interval "%s" %f:%f>' % (self.__mark, self.__xmin, self.__xmax)

    def xmin(self):
        return self.__xmin

    def xmax(self):
        return self.__xmax

    def mark(self):
        return self.__mark

    def change_offset(self, offset):
        self.__xmin += offset
        self.__xmax += offset

    def change_text(self, text):
        self.__mark = text


class Point:

    """represents a Point"""

    def __init__(self, time, mark):
        self.__time = time
        self.__mark = mark

    def __str__(self):
        return '<Point "%s" at %f>' % (self.__mark, self.__time)

    def time(self):
        return self.__time

    def mark(self):
        return self.__mark
