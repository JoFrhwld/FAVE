# What's new in version 2

Version 2.0.0 of FAVE was released February 10, 2022 replacing 1.3.1 which was released in October 2020. Like many software packages, FAVE follows the [semantic versioning](https://semver.org/) system, and the change from version 1 to version 2 means that this update introduces **changes that will break existing workflows**. The maintainers have made every attempt to keep the interface as similar to version 1 as possible, but long-time users will need to review and update their internal documentation and software to account for these new changes. To help this process, the FAVE maintainers have written this migration guide.

```{contents}
```

## Updating software

### Check your python version

```{note}
We say FAVE runs on Python 3, but that's a little vague. Python 3.0 is 14 years old and like Python 2 no longer receives security updates. In order to run FAVE 2 you need at least Python 3.8, and we recommend using the latest stable version of Python.
```

You can check your current version of python using:

```{code-block} console
:caption: Check your python version

python --version
```

If that command outputs a version 3.8 or higher (so 3.9, 3.10, etc.) then you have the proper python version installed.

If you get a version like 2.7, you should see if you *also* have Python 3 on your system:

```{code-block} console
:caption: Check Python 3 specifically

python3 --version
```

If that command outputs a version greater than 3.8, then you have a proper version. If it outputs a version *less* than that, like 3.5 or 3.7, you will need to install a newer version of python.

If the command fails, then you do not have any python 3 version installed and you will need to install a compatible version.

```{note}
You can download the latest python version from [the Python Software Foundation website](https://www.python.org/downloads/). Once downloaded, install as instructed, and then go through the above steps again to check that the installation was successful.
```

### Installing FAVE

Install FAVE using Python's built-in software package manager pip:

```{code-block} console
:caption: Install FAVE using pip

python3 -m pip install fave
```

```{note}
Older versions of FAVE could simply be downloaded and ran. Unlike previous versions FAVE 2 needs to be *installed*.
```

## Aligning and extracting with FAVE 2

```{warning}
The argument order and behavior has changed in version 2. Double check the documentation to make sure that you're using the right commands.
```

FAVE can still be run as a command-line program using `FAAValign.py` and `extractFormants.py`, but the location and syntax for these files have changed slightly. These scripts come with help documentation. In a terminal, navigate to the FAVE folder (containing files like LICENSE and README) and run one of the following commands for details on how to run the script.

```{code-block} console
:caption: Usage help from command line

python3 fave/FAAValign.py --help
python3 fave/extractformants.py --help
```

```{note}
Development is ongoing to have these scripts installed system wide, but as of 2.0.1, you may still need to download them and run them directly.
```

### Aligning using FAAValign.py

Before aligning, you should check the transcription for out-of-dictionary words. For this you use the `-c` or `--check` flag, followed by the name of a file where any unknown words should be listed.

```{code-block} console
:caption: Check for unknown transcriptions

python3 fave/FAAValign.py --check unknown_words.txt AudioFile.wav TranscriptionFile.txt OutputAlignment.TextGrid
```

You can then create your own transcriptions for these words, and include them in the aligning process using the `-i` or `-import` flag.

```{code-block} console
:caption: Include custom dictionary file

python3 fave/FAAValign.py --import custom_dictionary.txt AudioFile.wav TranscriptionFile.txt OutputAlignment.TextGrid
```

```{note}
It is best to *always* specify the sound file, transcript file, and output file.

If the transcript file or output file are omitted, FAVE will do its best to assume a sensible name based on the sound file name, but this may not always work.

If you run into errors, try specifying the transcript and output file names.
```

### Getting vowel data using extractFormants.py

Formant data for vowels can be extracted using:

```{code-block} console
:caption: Extract formant data

python3 fave/extractFormants.py AudioFile.wav Alignment.TextGrid OutputFileName.tsv
```

If you used the Montral Forced Aligner to align your transcript, you should include the `--mfa` flag when extracting formant data.

```{code-block} console
:caption: Extract data from MFA alignment

python3 fave/extractFormants.py --mfa AudioFile.wav Alignment.TextGrid OutPutFileName.tsv
```

```{note}
The formant extraction process is *highly* customizable and these can be configured from the command line using flags. To see a list of all the configuration options, run the script with the `-h` or `--help` flags.
```

## The FAVE Python module

```{note}
The documentation of FAVE's API is in {doc}`the code documentation section <../code/index>`.
```

New to version 2 is the ability to `import` FAVE as a python module. This allows you to use FAVE in custom scripts for things like batch alignment, extraction, or customizing the behavior during alignment.

```{code-block} python
:caption: Example of loading a FAVE module

from fave.align import TranscriptProcessor
```

## Frequently Asked Questions

### What was wrong with the old FAVE?

FAVE is written in the Python programming language. Python v2 was released in 2000 and was the langauge FAVE was written for. In 2006 development began on Python v3 which was released in 2008. Python 2 was scheduled to reach end-of-life in 2015, 7 years after the release of Python 3. In 2014, that sunset date was extended to 2020, and on January 1, 2020, 12 years after the release of Python 3, the developers announced that Python 2 was no longer supported. It would not receive bug fixes, and any security vulnerabilities would not be fixed. All users who had not already migrated to Python 3 were instructed to do so as soon as possible. As of August 2022, Python 3.10.4 is the current stable version. You can read [the full history from the Python Software Foundation](https://www.python.org/doc/sunset-python-2/).

FAVE, being written for Python 2, was not compatible with the latest versions of Python. [Continuing to use Python 2 increases security risks](https://www.darkreading.com/vulnerabilities-threats/continued-use-of-python-2-will-heighten-security-risks) and it would be irresponsible to ask researchers holding sensitive personal data to introduce a security risk into their systems when other options are available. In 2020, maintainers Josef Freuhwald and Christian Brickhouse began rewriting FAVE to be compatible with Python 3. This migration was completed and released as FAVE 2.0.0 in February 2022.

### Why does the new version work differently?

FAVE is old software, and as software ages it accumulates changes that make it more complex. Bandaids, duct tape, patches, and other fixes are applied as needed to make sure the code keeps running for those who rely on it. Over time, the people who introduced and understood why and how these quick fixes worked leave, and often the knowledge leaves with them. What remains is a large, complex program that is hard to fix and even harder to add new features to. Among software programmers, this is known as [techincal debt](https://en.wikipedia.org/wiki/Technical_debt). FAVE was not migrated to Python 3 sooner because doing so was risky. The size and complexity of the program made it likely that even small changes might cause problems in other areas, and so the software was left as-is until the deprecation of Python 2 forced migration.

To avoid this situation in the future, the migration to Python 3 also included changes which made the code easier to maintain. Since maintainers would be reading through all of the code to make sure it worked with Python 3, it was a good time to start repaying technical debt. The code was restructured so that it could easily be imported into python scripts as a module, and new workflows were created to allow for easier installation of the program and its dependencies. These improvements came with trade-offs, and in order to structure the code in a way that made it easy to udnerstand, maintain, and build new features on top of, we needed to make some changes to the previous interface.
