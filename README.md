# FAVE toolkits

This is a repository for the FAVE-Align and FAVE-extract toolkits.
The first commit here represents the toolkit as it was available on the FAVE website as of October 21, 2013.
The extractFormants code in the JoFrhwld/FAAV repository represents an earlier version of the code.

## Getting started

You can install FAVE using pip by running the following:
```
python3 -m pip install fave
```

While FAVE can align transcripts to audio data, we recommend using the [Montreal Force Aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/first\_steps/index.html#first-steps-align-pretrained) for alignment because it is more recent and better maintained than the HTK library used by FAVE's aligner.

When you have an aligned TextGrid and the matching audio, you can extract acoustic measures by running the following:
```
fave-extract AudioFileName.wav TextGridFileName.TextGrid OutputFileName
```

Where `AudioFileName.wav` is the path to the audio file to measure, `TextGridFileName.TextGrid` is the path to the aligned TextGrid, and `OutputFileName` is the name of the file where you want your measurements to be output.

## Documentation
Current documentation for installation and usage available on the github wiki. [https://github.com/JoFrhwld/FAVE/wiki](https://github.com/JoFrhwld/FAVE/wiki)

## FAVE website

The interactive FAVE website hosted at the University of Pennsylvania is no longer available. The DARLA site hosted by Dartmouth can be used to run the Montreal Forced Aligner, and FAVE-extract. [http://darla.dartmouth.edu](http://darla.dartmouth.edu)

## Support

You can find user support for installing and using the FAVE toolkits at the [FAVE Users' Group](https://groups.google.com/forum/#!forum/fave-users).

## Contributing to FAVE
For the most part, we'll be utilizing the fork-and-pull paradigm (see [Using Pull Requests](https://help.github.com/articles/using-pull-requests)). Please send pull requests to the `dev` branch.

To fill a bug report, please follow this link [Bug Report](/.github/ISSUE_TEMPLATE/bug_report.yml)

## Attribution
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.22281.svg)](http://dx.doi.org/10.5281/zenodo.22281)
As of v1.1.3 onwards, releases from this repository will have a DOI associated with them through Zenodo. The DOI for the current release is [10.5281/zenodo.22281](http://dx.doi.org/10.5281/zenodo.22281). We would recommend the citation:

Rosenfelder, Ingrid; Fruehwald, Josef; Brickhouse, Christian; Evanini, Keelan; Seyfarth, Scott; Gorman, Kyle; Prichard, Hilary; Yuan, Jiahong; 2022. FAVE (Forced Alignment and Vowel Extraction) Program Suite v2.0.0 */zenodo.*

Use of the interactive online interface should continue to cite:

Rosenfelder, Ingrid; Fruehwald, Josef; Evanini, Keelan and Jiahong Yuan. 2011. FAVE (Forced Alignment and Vowel Extraction) Program Suite. http://fave.ling.upenn.edu.
