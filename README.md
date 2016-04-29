# FAVE toolkits

This is a repository for the FAVE-Align and FAVE-extract toolkits.
The first commit here represents the toolkit as it was available on the FAVE website as of October 21, 2013.
The extractFormants code in the JoFrhwld/FAAV repository represents an earlier version of the code.

## FAVE website

The interactive website for utilizing FAVE can be found at [fave.ling.upenn.edu](http://fave.ling.upenn.edu/)

## Building and running with Docker

The included Docker (www.docker.com) file can be used to simplify the process of building and running FAVE. Install Docker according to the instructions for your platform ([Mac](https://docs.docker.com/engine/installation/mac/), [Windows](https://docs.docker.com/engine/installation/windows/), [Linux](https://docs.docker.com/engine/installation/linux/)).

To install, clone this repository as described in the [FAVE-align instructions](/wiki/Installing-FAVE-align#downloading-fave-align). Download the [HTK-3.4.1.tar.gz file](http://htk.eng.cam.ac.uk/download.shtml) (registration required) into the root of the repository (e.g. `Downloads/FAVE`; no need to unpack it). Run docker_build.sh (Mac or Linux only) or issue the command `docker build -t fave [FAVE_DIRECTORY]` where \[FAVE_DIRECTORY\] is the location of this repository on your disk. 

To run FAVE-align from your Docker environment, issue commands along the following lines, modifying them according to the options documented in the FAVE-align and FAVE-extract scripts themselves:

``` sh
# Basic alignment run 
docker run -it -v /path/to/audio/and/text/folder:/opt/audio fave 'FAAValign.py -v /opt/audio/my_audio.wav'
# Check words
docker run -it -v /path/to/audio/and/text/folder:/opt/audio fave 'FAAValign.py -vc /opt/audio/unknown_words.txt /opt/audio/my_audio.wav'
# Use custom pronounciations (put them with your transcripts, or investigate the --volume option for Docker)
docker run -it -v /path/to/audio/and/text/folder:/opt/audio fave 'FAAValign.py -vi /opt/audio/new_words.txt /opt/audio/my_audio.wav'
# Use a custom dictionary
docker run -it -v /path/to/audio/and/text/folder:/opt/audio -v /my/custom/dict:/opt/dict fave 'FAAValign.py -v --dict /opt/dict /opt/audio/my_audio.wav'
```
Output textgrids will end up in the same folder as your audio and transcripts, as is normally the case in FAVE-align.

## Support

You can find user support for installing and using the FAVE toolkits at the [FAVE Users' Group](https://groups.google.com/forum/#!forum/fave-users).

## Contributing to FAVE
For the most part, we'll be utilizing the fork-and-pull paradigm (see [Using Pull Requests](https://help.github.com/articles/using-pull-requests)). Please send pull requests to the `dev` branch.

If you want to keep up to date on FAVE development, or have questions about FAVE development, send a request to join the [FAVE Developers' Group](https://groups.google.com/forum/#!forum/fave-dev).

## Attribution
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.22281.svg)](http://dx.doi.org/10.5281/zenodo.22281)
As of v1.1.3 onwards, releases from this repository will have a DOI associated with them through Zenodo. The DOI for the current release is [10.5281/zenodo.22281](http://dx.doi.org/10.5281/zenodo.22281). We would recommend the citation:

Rosenfelder, Ingrid; Fruehwald, Josef; Evanini, Keelan; Seyfarth, Scott; Gorman, Kyle; Prichard, Hilary; Yuan, Jiahong; 2014. FAVE (Forced Alignment and Vowel Extraction) Program Suite v1.2.2 10.5281/zenodo.22281

Use of the interactive online interface should continue to cite:

Rosenfelder, Ingrid; Fruehwald, Josef; Evanini, Keelan and Jiahong Yuan. 2011. FAVE (Forced Alignment and Vowel Extraction) Program Suite. http://fave.ling.upenn.edu.
