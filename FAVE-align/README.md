# FAVE-align

For more information on the installation and use of FAVE-align, see the associated GitHub wiki pages: 
https://github.com/JoFrhwld/FAVE/wiki/FAVE-align

## Installation

### Dependencies

FAVE-align depends on **[HTK](http://htk.eng.cam.ac.uk/)** and **[SoX](http://sox.sourceforge.net/)** to work. 
As such, you'll need to have these installed.

As HTK requires modification of its source code to work properly, it is *strongly encouraged* that you refer to the GitHub wiki page on the topic (https://github.com/JoFrhwld/FAVE/wiki/HTK-3.4.1) even if you feel confident in what you're doing.

Otherwise [the FAVE GitHub wiki](https://github.com/JoFrhwld/FAVE/wiki) contains the relevant documentation for the installation and configuration of HTK and SoX.

## Usage

Usage:  

    python FAAValign.py [options] soundfile.wav [transcription.txt] [output.TextGrid]

Aligns a sound file with the corresponding transcription text. 
The transcription text is split into annotation breath groups, which are fed individually as "chunks" to the forced aligner. 
All output is concatenated into a single Praat TextGrid file.

### INPUT:

- sound file
- tab-delimited text file with the following columns:
    * first column:   speaker ID
    * second column:  speaker name
    * third column:   beginning of breath group (in seconds)
    * fourth column:  end of breath group (in seconds)
    * fifth column:   transcribed text

(If no name is specified for the transcription file, it will be assumed to have the same name as the sound file, plus ".txt" extension.)

### OUTPUT:
- Praat TextGrid file with orthographic and phonemic transcription tiers for
each speaker (If no name is specified, it will be given same name as the sound
file, plus ".TextGrid" extension.)


### Options:

Short | Long | Description
------ | -----| ------
 | `--version`  | Prints the program's version string and exits.
`-h` | `--help`  | Shows the help message and exits.
`-c [filename]` | `--check=[filename]`  | Checks whether phonetic transcriptions for all words in the transcription file can be found in the CMU Pronouncing Dictionary (file `dict`).  Returns a list of unknown words.
`-i [filename]` | `--import=[filename]`  | Adds a list of unknown words and their corresponding phonetic transcriptions to the CMU Pronouncing Dictionary prior to alignment.  User will be prompted interactively for the transcriptions of any remaining unknown words.  File must be tab-separated plain text file.
`-v` | `--verbose` | Detailed output on status of dictionary check and alignment progress.
`-d [filename]` | `--dict=[filename]` | Specifies the name of the file containing the pronunciation dictionary.  Default file is `/model/dict`.
`-n` | `--noprompt` | User is not prompted for the transcription of words not in the dictionary, or truncated words.  Unknown words are ignored by the aligner.
