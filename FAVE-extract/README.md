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

There are many configuration parameters that can alter the behavior of extractFormants.  
The user can modify their values by creating a config file; otherwise, default values will be set internally.  
To use a config file, use the argument `--config=` followed by the name of the config file.  For example, to load a configuration file named 'config.txt' located in the current directory, type:

`$ python bin/extractFormants.py --config=config.txt filename.wav filename.TextGrid outputFile`

The syntax of the config file is as follows:

`parameter=value`

I.e., each line contains first the name of the configuration parameter, then '=', then the value that this parameter should take.

Here is a list of all of the configuration parameters that can be set by the user in the config file, along with their possible values and the default value that is set internally (the default value is listed first surrounded by asterisks).


Parameter	|	=default (other possible values)
---------	| -------------	
`speechSoftware`	|	`=praat` (`esps`)
`multipleFiles`	|	`=F` (`T`)
`removeStopWords`	|	`=F` (`T`)
`measureUnstressed`	| `=T` (`F`)
`minVowelDuration` |	`=0.05` (any value >`0`, or `0` to not use)
`case`	|		`=upper` (`lower`)
`outputFormat`	|	`=text` (`plotnik`, `both`)
`outputHeader`	|	`=T` (`F`)
`formantPredictionMethod`	 | `=mahalanobis` (`default`)
`measurementPointMethod` |	`=faav`, (`third`, `mid`, `fourth`, `lennig`, `anae`)
`nFormants`	|	`=5` (an integer typically between `3` and `7`)
`maxFormant`	|	`=5000` (any integer)
`windowSize`|	`=0.025`
`preEmphasis`	|	`=50`
`nSmoothing`	|	`=12`
`remeasurement`	|	`=F` (`T`)
`candidates`	|	`=F` (`T`)
`vowelSystem`	 |	`=NorthAmerican` (`Phila`)


For example, here are the contents of a possible configuration file:

	speechSoftware=praat
	measureUnstressed=F
	minVowelDuration=0.03
	formantPredictionMethod=mahalanobis

This file specifies that Praat will be used as the speech analysis program (this line is actually redundant here, since Praat is set internally to be the default speech software), that unstressed vowels will not be measured, that vowels shorter than 30 msec will not be measured, and that the vowel formants will be predicted using the Mahalanobis distance algorithm described in Evanini (2009).

Here is a description of the function of all of the parameters.

Parameter | Description
----------|------------
`speechSoftware` | The speech software program to be used for LPC analysis
`multipleFiles` | If true, then the three command line arguments are namesof files that contain lists of the WAV files, TextGrid files and output files.  All three files must have the same number of items and they must be in the same order in each.
`removeStopWords` | If `T`, then vowels in stop words are not measured.  A basic list of stop words including prepositions and other function words (the words most likely to have reduced vowels) is included in extractFormants.  The user can specify a list of stop words in a file with the command line argument `--stopWords`.
`measureUnstressed`  |  If `F`, then vowels marked with 0 stress in the pronouncing dictionary are not measured.  If `T`, then all vowels are measured.
`minVowelDuration`  |  Any vowel with a duration shorter than this value (in seconds) will not be measured (use this to minimize the number of reduced vowels that are measured).
`case` | 	If `upper`, then word transcriptions are output in upper case in the output file.  If `lower`, then lower case (this makes visual displays in, e.g., Plotnik easier to read, since each word takes up less space).
`outputFormat` | If `text`, then the vowel formant measurements are output to a tab-delimited file.  If `plotnik`, then the output is a Plotnik file.  If `both`, then both output files are produced.  See Section V for details about interpreting the contents of these files.
`outputHeader` | If `T`, then a header row is output as the first line of the text output file.  If `false`, then no header row is output.  Only applies if `outputFormat=text`.
`formantPredictionMethod` | If `default`, then the default formant values produced by the speech analysis program (either Praat or ESPS) are used.  If `mahalanobis`, then the formant prediction algorithm from Evanini (2009) is used.  This algorithm compares all poles and bandwidths returned by the LPC analysis for the vowel to a distribution of expected formant poles and bandwidths taken from the ANAE measurements.  In order to use the `mahalanobis` option, the files containing the means and covariance matrices must be available.  The default files are `means.txt` and `covs.txt`, included with the distribution.
`measurementPointMethod` | This parameter determines at which point within the vowel the formant measurements are taken.  `third` measures the vowel formants at one third of the vowel's duration.  `mid` measures at the vowel's midpoint, and `fourth` at one fourth of the vowel's duration.  `lennig` uses the algorithm from Lennig (1978) to find a steady state within the vowel.  `anae` uses the guidelines from Labov, Ash & Boberg (2006), namely, to measure at an F1 maximum.  The default method, `faav`, modifies the `third` method in that /ay/, /ey/ are measured at maximum F1, /ow, aw/ halfway between maximum F1 and the beginning of the vowel, and /Tuw/ (/uw/ after coronal consonants) at the beginning of the vowel.
`nFormants` | Specifies the number of formants to be returned, i.e., specify the order of the LPC analysis to be conducted.  Only used if the speech analysis software is Praat.
`maxFormant` | Specifies the maximum frequency to consider for vowel formants.  Only used if the speech analysis software is Praat.  Praat recommends a default value of 5000 Hz for male speakers and 5500 for females.  However, adjustment may be necessary on a per-speaker basis to obtain the optimal values for this parameter and `nFormants`.
`windowSize` | In sec, the size of the Gaussian window to be used for LPC analysis.  Only used if the speech analysis software is Praat (see the Praat manual for further details).
`preEmphasis` | The cut-off value in Hz for the application of a 6 dB/octave low-pass filter.  Only used if the speech analysis software is Praat (see the Praat manual for further details).
`nSmoothing` | Specifies the number of samples to be used for the smoothing of the formant tracks.  The window size for the running average will be (2 * nSmoothing + 1).  Default value is 12, which corresponds to a 25 ms window.
`remeasurement` | Specifies whether a second pass is performed on the data, using the speaker's own system as the base of comparison for the Mahalanobis distance.  Only used if `formantPredictionMethod=mahalanobis`.
`candidates` | Specifies whether the list of candidate formant values are included in the output.  Only used if the `outputFormat=text`.
`vowelSystem` | If set to `Phila`, a number of vowels will be reclassified to reflect the phonemic distinctions of the Philadelphia vowel system (tense short-a etc.).


References
----------

* Evanini, Keelan.  2009.  Doctoral dissertation, University of Pennsylvania.
* Labov, William, Sharon Ash, and Charles Boberg.  2006.  The Atlas of North American English.  Mouton de Gruyter.
* Lennig, Matthew.  1978.  Acoustic measurement of linguistic change:  The modern Paris vowel system.  Doctoral dissertation, University of Pennsylvania.
