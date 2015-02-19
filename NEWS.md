NEWS

v.1.2.1

* AH0 is now mapped to schwa (`plt_vclass = @`) instead of wedge. (@jofrhwld)
* When a vowel class isn't in means.txt or covs.txt, default to `nFormants = 5` for first pass. This was necessary to support schwa (@jofrhwld)
* Fix for smart quotes in transcription (@kevanini)
* Command-line argument for HTKTOOLSPATH (@kevanini)

v1.2

* Two major updates to user interface with FAVE-extract. (@jofrhwld)

	## Update to Options

	There was an internal change to how arguments and options are processed (now using argparse), leading a change in how users should organize their config.txt files. The old format looked like this:

	    -outputFormat=txt
	    -formantPredictionMethod=mahalanobis

	The new format looks like this

	    --outputFormat
	    txt
	    --formantPredictionMethod
	    mahalanobis

	The way the config.txt file was passed to extractFormants.py has also changed. It used to be done like so

	    > python bin/extractFormants.py config=config.txt wavfile textgridfile outputfile

	It is now done like this:

   	    > python bin/extractFormants.py +config.txt wavfile textgridfile outputfile

	Is now also possible to define any option in the commandline call to extractFormants.py itself. For example, it is possible to define an option like so:
	
	    > python bin/extractFormants.py --minVowelDuration 0.3 wavfile textgridfile outputfile

	We would still recommend defining you config options in a config.txt file for ease, but however options are passed to extractFormants.py, the complete set of options and their settings will still be written to the log file.

	## Update to Output

	The text output has been heavilly revamped to be more conventional. Nothing has been removed from the output, but some things have been restructured, and some additional contextual information has been added. For example, the text output used to include vowel category information in a column labelled `cd`, with the data included as numerical Plotnik codes. In the new format, this data is included in a column called `plt_vclass`, and given as a (slightly modified) Labovian notation.


* FAVE-align is now compatible with Windows (@scjs)

* stop words are now logged correctly when using a custom stop words file. `opts.stopWords` takes the place of global `stopWords` everywhere (@scjs)

* case for both the preceding and following word transcriptions is now correctly changed before the measurement is recorded (@scjs)

* `pickle` files are written in binary mode to avoid issues with imported classes (@scjs)

* FAVE-align now only uses the file extension when checking that wav and txt input files are the correct type, instead of redundantly verifying both the extension and a MIME type that was guessed from the extension (@scjs)

* invalid or missing segments adjacent to the vowel that is being measured are now recorded as `''` (empty string) rather than `NA`, for consistency (@scjs)

* FAVE-align now uses `os` and `shutil` module functions instead of OS-specific shell commands (@scjs)

* FAVE-extract now uses `splitlines()` instead of stripping `\n` when parsing multiple input files or a stopwords file (@scjs)

* new config option --traks will write full formant trakcs to a *_tracks.txt file (@jofrhwld)
