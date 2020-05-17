For more information on the installation and use of FAVE-extract, see the associated pages on the GitHub wiki:
https://github.com/JoFrhwld/FAVE/wiki/FAVE-extract

# Contents

I. [System Requirements](#i-system-requirements)

II. [Usage](#ii-usage)

III. [Changing Configuration Parameters](#iii-changing-configuration-parameters)

## I. System requirements ##

FAVE-extract has a number of dependencies which must be installed before it will will be usable. These are

* SoX http://sox.sourceforge.net/
* Praat http://www.praat.org/
* numpy http://www.scipy.org/install.html#individual-binary-and-source-packages

See the GitHub wikipage on installing FAVE-extract for more information on installing these dependencies. 
https://github.com/JoFrhwld/FAVE/wiki/Installing-FAVE-extract


## II. Usage ##

Currently, FAVE-extract is set up so that it must be run from the main directory of the FAVE-extract package.  
To run FAVE-extract, three arguments are required:  
* the WAV file containing the speech data, 
* the TextGrid file containing the alignments, 
* and the name of an output file for the extracted formants.  

So, in the directory `FAVE-extract`, type:

    python bin/extractFormants.py filename.wav filename.TextGrid outputFile

## III Changing configuration parameters ##

There are many configuration parameters that can alter the behavior of `extractFormants.py`.
These can all be passed to `extractFormants.py` either with flags at the commandline, or put into a config file.
For example, this call to `extractFormants.py` specifies a text output, measuring vowels one third of the way through their duration, and applying remeasurement.

`$ python bin/extractFormants.py --outputFormat txt --measurementPointMethod third --remeasure filename.wav filename.TextGrid outputFile`

Alternatively, you could create a config file called `config.txt` formatted like so:
    
    --outputformat
    txt
    --measurementPointMethod
    third
    --remeasure

You would pass these options to `extractFormants.py` like so:

`$ python bin/extractFormants.py +config.txt filename.wav filename.TextGrid outputFile`

Here is a list of all of the configuration parameters that can be set by the user, along with their possible values and the default value that is set if no value is explicitly set. 
A number of flags don't take a specific value (e.g. `--candidates`, `--remeasurement`, `--verbose`).
Simply providing these flags alters `extractFormants.py`'s behavior.

Parameter	|	default (other possible values) | description
---------	| -------------	| ----------------
`--candidates`| | Return all candidate measurements in output
`--case` | `upper` (`lower`)  | If `upper`, then word transcriptions are output in upper case in the output file.  If `lower`, then lower case (this makes visual displays in, e.g., Plotnik easier to read, since each word takes up less space).
`--covariances`, `-r` | `covs.txt` (covariance file) | covariances, required for mahalanobis method
`--formantPredictionMethod`| `mahalanobis` (`default`) |If `default`, then the default formant values produced by the speech analysis program (either Praat or ESPS) are used.  If `mahalanobis`, then the formant prediction algorithm from Evanini (2009) is used.  This algorithm compares all poles and bandwidths returned by the LPC analysis for the vowel to a distribution of expected formant poles and bandwidths taken from the ANAE measurements.  In order to use the `mahalanobis` option, the files containing the means and covariance matrices must be available.  The default files are `means.txt` and `covs.txt`, included with the distribution. Different means and covariances can be specified with the flaggs `--means` and `--covariances`
`--maxFormant` | `5000` | Specifies the maximum frequency to consider for vowel formants.  Only used if the speech analysis software is Praat.  Praat recommends a default value of 5000 Hz for male speakers and 5500 for females.  However, adjustment may be necessary on a per-speaker basis to obtain the optimal values for this parameter and `nFormants`.
`--means`,`-m` | `means.txt` (means file) | mean values, required for mahalanobis method
`--measurementPointMethod` | `faav` (`fourth`,`third`,`mid`,`lennig`,`anae`,`maxint`)| This parameter determines at which point within the vowel the formant measurements are taken.  `third` measures the vowel formants at one third of the vowel's duration.  `mid` measures at the vowel's midpoint, and `fourth` at one fourth of the vowel's duration.  `lennig` uses the algorithm from Lennig (1978) to find a steady state within the vowel.  `anae` uses the guidelines from Labov, Ash & Boberg (2006), namely, to measure at an F1 maximum.  The default method, `faav`, modifies the `third` method in that /ay/, /ey/ are measured at maximum F1, /ow, aw/ halfway between maximum F1 and the beginning of the vowel, and /Tuw/ (/uw/ after coronal consonants) at the beginning of the vowel.
`--minVowelDuration` | 0.05 | Any vowel with a duration shorter than this value (in seconds) will not be measured (use this to minimize the number of reduced vowels that are measured).
`--multipleFiles` | | If provided, then the three command line arguments are names of files that contain lists of the WAV files, TextGrid files and output files.  All three files must have the same number of items and they must be in the same order in each.
`--nFormants` | 5 | Specifies the number of formants to be returned, i.e., specify the order of the LPC analysis to be conducted.  Only used if the speech analysis software is Praat. 
`--noOutputHeader` | | If provided, the header row will be ommitted from the output (relevant to only text output)
`--nSmoothing` | `12` | Specifies the number of samples to be used for the smoothing of the formant tracks.  The window size for the running average will be (2 * nSmoothing + 1).  Default value is 12, which corresponds to a 25 ms window.
`--onlyMeasureStressed` | | If provided, only stressed vowels will be measured.
`--outputFormat` `-o`| `txt` (`text`,`plotnik`,`Plotnik`,`plt`,`both`) | If `text`, then the vowel formant measurements are output to a tab-delimited file.  If `plotnik`, then the output is a Plotnik file.  If `both`, then both output files are produced. 
`--preEmphasis` | `50` | The cut-off value in Hz for the application of a 6 dB/octave low-pass filter.  Only used if the speech analysis software is Praat (see the Praat manual for further details).
`--phoneset`, `-p` | `cmu_phoneset.txt` | 
`--remeasurement` | | Specifies whether a second pass is performed on the data, using the speaker's own system as the base of comparison for the Mahalanobis distance.  Only used if `formantPredictionMethod=mahalanobis`.
`--removeStopWords` | |  If provided, then vowels in stop words are not measured.  A basic list of stop words including prepositions and other function words (the words most likely to have reduced vowels) is included in extractFormants.  The user can specify a list of stop words in a file with `--stopWords` or `--stopWordsFile`.
`--speechSoftware` | `praat` (`Praat`,`esps`,`ESPS`) |The speech software program to be used for LPC analysis.
`--speaker`, `-s` | (speaker file) | *.speaker file, if used
`--stopWords` | [STOPWORDS ...] | Words to be excluded from measurement. This should be the last argument, after the positional arguments, if used.
`--stopWordsFile`, `-t` | (stop words file) | File containing words to exclude from analysis.
`--vowelSystem` | `NorthAmerican` (`phila`,`Phila`,`PHILA`,`NorthAmerican`,`simplifiedARPABET`) | If set to `Phila`, a number of vowels will be reclassified to reflect the phonemic distinctions of the Philadelphia vowel system (tense short-a etc.).
`--verbose`, `-v` | | If provided, verbose output. useful for debugging
`--windowSize` | `0.025` | In sec, the size of the Gaussian window to be used for LPC analysis.  Only used if the speech analysis software is Praat (see the Praat manual for further details).


References
----------

* Evanini, Keelan.  2009.  Doctoral dissertation, University of Pennsylvania.
* Labov, William, Sharon Ash, and Charles Boberg.  2006.  The Atlas of North American English.  Mouton de Gruyter.
* Lennig, Matthew.  1978.  Acoustic measurement of linguistic change:  The modern Paris vowel system.  Doctoral dissertation, University of Pennsylvania.
