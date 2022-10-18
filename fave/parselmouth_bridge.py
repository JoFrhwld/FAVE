import parselmouth
from deprecated.sphinx import versionadded

@versionadded(version="2.1")
class Formant():
    """Bridge the parselmouth.Formant API with our scripting needs.
    """
    def __init__(self, formant_obj, maxFormant):
        """Create an instance from a parselmouth.Formant instance
        
        :param formant_obj: A parselmouth.Formant instance.
        :param maxFormant: Currently unused
        """
        self.__pm_formant = formant_obj
        self.__maxFormant = maxFormant
        self.intensities = []
    
    def __formant_iter( self, function, range_ ):
        """Takes a callback function from parselmouth.Formant and applies a loop

        :param function: A parselmouth.Formant method which will be called in this loop.
        :type function: function
        :param range_: A tuple or list passed to `range()` specifying which formants to loop over.
            N.B. `range_` is inclusive on the lower bound, exclusive on the upper bound, so (1,4) will 
            give formants 1 through 3, and not 4.
        :type range_: tuple|list
        :return: The measures output by the callback function. Each list item is a list of formant
            measurements for the given time input.
        :rtype: list
        """
        ret = []
        for t in self.times():
            vals = []
            for n in range(*range_):
                vals.append( function(formant_number = n, time = t) )
            ret.append(vals)
        return ret

    def times(self):
        """Wrapper around parselmouth.Formant.ts

        :rtype: list
        """
        return list(self.__pm_formant.ts())

    def formants(self, range_ = (1,4)):
        """Returns formant measures at each time point.

        :param range_: The range of formants to measure passed to `range()`, defaults to (1,4).
            N.B. `range_` is inclusive on the lower bound, exclusive on the upper bound, so (1,4) will 
            give formants 1 through 3, and not 4.
        :type range_: tuple|list
        :return: Formant measurements. Each list item is a list of formant
            measurements for the given time input.
        :rtype: list
        """
        return self.__formant_iter(
                self.__pm_formant.get_value_at_time,
                range_
            )

    def bandwidths(self, range_ = (1,4)):
        """Returns formant bandwidth measures at each time point.

        :param range_: The range of formants to measure passed to `range()`, defaults to (1,4).
            N.B. `range_` is inclusive on the lower bound, exclusive on the upper bound, so (1,4) will 
            give formants 1 through 3, and not 4.
        :type range_: tuple|list
        :return: Bandwidth measurements. Each list item is a list of bandwidth
            measurements for the given time input.
        :rtype: list
        """
        return self.__formant_iter(
                self.__pm_formant.get_bandwidth_at_time,
                range_
            )

    def xmin(self):
        """Wrapper around parselmouth.Formant.xmin

        :rtype: float?
        """
        return self.__pm_formant.xmin
    
    def xmax(self):
        """Wrapper around parselmouth.Formant.xmax

        :rtype: float?
        """
        return self.__pm_formant.xmax

    def n(self):
        """Wrapper around parselmouth.Formant.nx

        :rtype: int?
        """
        return self.__pm_formant.nx

    @property
    def intensities(self):
        return self.__intensities

@versionadded(version="2.1")
class Intensity():
    def __init__(self, pm_intensity):
        self.__pm_intensity = pm_intensity
        self.offset = 0

    def xmin(self):
        return self.__pm_intensity.xmin + self.offset

    def xmax(self):
        return self.__pm_intensity.xmax + self.offset

    def n(self):
        return self.__pm_intensity.n

    def nx(self):
        return self.__pm_intensity.nx

    def dx(self):
        return self.__pm_intensity.dx

    def x1(self):
        return self.__pm_intensity.x1 + self.offset

    def times(self):
        return [x + self.offset for x in list(self.__pm_intensity.ts())]

    def intensities(self):
        return [self.__pm_intensity.get_value(time = t) for t in self.times()]

    def change_offset(self, offset):
        self.offset = offset

    def __str__(self):
        return '<Intensity object with %i frames>' % self.__n

    def __iter__(self):
        return iter(self.__intensities)

    def __len__(self):
        return self.__n

    def __getitem__(self, i):
        """returns the (i+1)th intensity frame"""
        return self.intensities()[i]
