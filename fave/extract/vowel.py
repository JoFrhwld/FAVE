#
# !!! This is NOT the original vowel.py file !!!          ##
#
# Last modified by Ingrid Rosenfelder:  February 25, 2010            ##
# - syntax as in last function (checking for list membership)        ##
# - doc strings for all functions                                    ##
# - functions ordered alphabetically                                 ##
#


def isDiphthong(v):
    """checks whether a vowel is a true diphthong (ay, aw, oy)"""
    if v in ["AW", "AY", "OY"]:
        return 1
    else:
        return 0


def isIngliding(v):
    """checks whether a vowel is ingliding (ae, ah)"""
    if v in ["AE", "AO"]:
        return 1
    else:
        return 0


def isShort(v):
    """checks whether a vowel is short (o, e, i, u, ^)"""
    if v in ["AA", "EH", "IH", "UH", "AH"]:
        return 1
    else:
        return 0


def isUpgliding(v):
    """checks whether a vowel is upgliding (iy, ey, ay, oy, uw, ow, aw)"""
    if v in ["IY", "EY", "AY", "OY", "UW", "OW", "AW"]:
        return 1
    else:
        return 0
