#!/usr/bin/env python3
# *_* coding: utf-8 *_*

"""
Command line utility for the FAVE library.
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

import argparse
import os
import logging
from shutil import which
from fave.align.aligner import Aligner

def defineArguments(parser): # pylint: disable=W0621
    """Define command line arguments"""
    global __version__ # pylint: disable=W0603
    parser.add_argument('--version', action='version', version='%(prog)s '+__version__)
    parser.add_argument(
        '-c',
        '--check',
        metavar='unknown.txt',
        default=None,
        help="""Checks whether phonetic transcriptions for all words in the
        transcription file can be found in the CMU Pronouncing Dictionary.
        Writes the unknown words to the specified file as tab delimited text."""
    )
    parser.add_argument(
        '-i',
        '--import',
        metavar='dict_file.txt',
        help="""Adds a list of unknown words and their corresponding phonetic
        transcriptions to the CMU Pronouncing Dictionary prior to alignment.
        User will be prompted interactively for the transcriptions of any
        remaining unknown words.  Required argument "FILENAME" must be
        tab-separated plain text file (one word - phonetic transcription pair
        per line)."""
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help="""Control how detailed the output of the program should be.""",
        action='count',
        default=0
    )
    parser.add_argument(
        '-d',
        '--dict',
        help="""Specifies the name of the file containing the pronunciation
        dictionary.  Default file is "/model/dict"."""
    )
    parser.add_argument(
        '-t',
        '--htktoolspath',
        default='',
        help="""Specifies the path to the HTKTools directory where the HTK
        executable files are located.  If not specified, the user's path will
        be searched for the location of the executable."""
    )
    parser.add_argument(
        "soundfile",
        nargs='?')
    parser.add_argument(
        "transcription",
        nargs='?',
        help="""tab-delimited text file with the following columns:
            first column:   speaker ID
            second column:  speaker name
            third column:   beginning of breath group (in seconds)
            fourth column:  end of breath group (in seconds)
            fifth column:   transcribed text
        (If no name is specified for the transcription file, it will be assumed to
        have the same name as the sound file, plus ".txt" extension.)""")
    parser.add_argument(
        "outputfile",
        nargs='?',
        help="""The name of a file where the output TextGrid will be written
        If no name is specified, it will be given same name as the sound
        file, plus ".TextGrid" extension."""
    )
    return parser

def parseArgs(**kwargs):
    """Check that the user input is sane and ideally handle errors before they happen"""
    for key in kwargs:
        if key in ['dict', 'import', 'soundfile', 'transcription'] and kwargs[key]:
            if not os.path.isfile(kwargs[key]):
                raise FileNotFoundError(kwargs[key])
    if kwargs['verbose'] == 1:
        level = logging.INFO
    elif kwargs['verbose'] > 1:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    kwargs['verbose'] = level
    kwargs['logfile'] = '.'.join(kwargs['soundfile'].split('.')[:-1])+'.FAAVlog'
    if kwargs['check']:
        # If check, first positional arg is transcript not sound file
        kwargs['transcription'] = kwargs['soundfile']
        kwargs['soundfile'] = None
    if not kwargs['htktoolspath'] and not kwargs['check']:
        if 'HTKTOOLSPATH' in os.environ:
            kwargs['htktoolspath'] = '$HTKTOOLSPATH'
        elif which('HVite') is None or which('HCopy') is None:
            raise ValueError('HTK Toolkit cannot be found. Unable to force align.')
    return kwargs

def main(**kwargs):
    """Main process for running an alignment. Ideally with same interface as FAAV 1.2"""
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        format='%(name)s - %(levelname)s:%(message)s',
        level=kwargs['verbose'])
    aligner = Aligner(
        kwargs['soundfile'],
        kwargs['transcription'],
        kwargs['outputfile'],
        **kwargs
    )
    aligner.read_transcript()
    aligner.check_transcript()
    aligner.check_against_dictionary()
    if not kwargs['check']:
        aligner.align()

def setup():
    parser = defineArguments(argparse.ArgumentParser(
        prog="FAAValign",
        description="""Aligns a sound file with the corresponding transcription text. The
        transcription text is split into annotation breath groups, which are fed
        individually as "chunks" to the forced aligner. All output is concatenated
        into a single Praat TextGrid file.""",
        epilog="""The following additional programs need to be installed and in the path:
        - Praat (on Windows machines, the command line version praatcon.exe)
        - SoX"""
    ))
    cliArgs = parseArgs(**vars(parser.parse_args()))
    main(**cliArgs)

if __name__ == "__main__":
    setup()
#else:
#    raise ImportError('FAAValign is a command line utility. Use the align module.')
