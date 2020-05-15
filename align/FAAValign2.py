def define_options_and_arguments():
	"""defines options and positional arguments for this program"""

	use = """(python) %prog [options] soundfile.wav [transcription.txt] [output.TextGrid]"""
	desc = """Aligns a sound file with the corresponding transcription text. The transcription text is split into annotation breath groups, which are fed individually as "chunks" to the forced aligner. All output is concatenated into a single Praat TextGrid file.

	INPUT:
	- sound file
	- tab-delimited text file with the following columns:
		first column:   speaker ID
		second column:  speaker name
		third column:   beginning of breath group (in seconds)
		fourth column:  end of breath group (in seconds)
		fifth column:   transcribed text
	(If no name is specified for the transcription file, it will be assumed to have the same name as the sound file, plus ".txt" extension.)

	OUTPUT:
	- Praat TextGrid file with orthographic and phonemic transcription tiers for each speaker (If no name is specified, it will be given same name as the sound file, plus ".TextGrid" extension.)"""

	ep = """The following additional programs need to be installed and in the path:
	- Praat (on Windows machines, the command line version praatcon.exe)
	- SoX"""

	vers = """This is %prog, a new version of align.py, written by Jiahong Yuan, combining it with Ingrid Rosenfelder's front_end_FA.py and an interactive CMU dictionary check for all words in the transcription file.
	Last modified May 14, 2010."""

	new_use = format_option_text(use)
	new_desc = format_option_text(desc)
	new_ep = format_option_text(ep)

	check_help = """Checks whether phonetic transcriptions for all words in the transcription file can be found in the CMU Pronouncing Dictionary.  Returns a list of unknown words (required argument "FILENAME")."""
	import_help = """Adds a list of unknown words and their corresponding phonetic transcriptions to the CMU Pronouncing Dictionary prior to alignment.  User will be prompted interactively for the transcriptions of any remaining unknown words.  Required argument "FILENAME" must be tab-separated plain text file (one word - phonetic transcription pair per line)."""
	verbose_help = """Detailed output on status of dictionary check and alignment progress."""
	dict_help = """Specifies the name of the file containing the pronunciation dictionary.  Default file is "/model/dict"."""
	noprompt_help = """User is not prompted for the transcription of words not in the dictionary, or truncated words.  Unknown words are ignored by the aligner."""
	htktoolspath_help = """Specifies the path to the HTKTools directory where the HTK executable files are located.  If not specified, the user's path will be searched for the location of the executable."""

	parser = optparse.OptionParser(usage=new_use, description=new_desc, epilog=new_ep, version=vers)
	parser.add_option('-c', '--check', help=check_help, metavar='FILENAME')						## required argument FILENAME
	parser.add_option('-i', '--import', help=import_help, metavar='FILENAME', dest='importfile')   ## required argument FILENAME
	parser.add_option('-v', '--verbose', action='store_true', default=False, help=verbose_help)
	parser.add_option('-d', '--dict', default='model/dict', help=dict_help, metavar='FILENAME')
	parser.add_option('-n', '--noprompt', action='store_true', default=False, help=noprompt_help)
	parser.add_option('-t', '--htktoolspath', default='', help=htktoolspath_help, metavar='HTKTOOLSPATH')

	## After parsing with (options, args) = parser.parse_args(), options are accessible via
	## - string options.check (default:  None)
	## - string options.importfile (default:  None)
	## - "bool" options.verbose (default:  False)
	## - string options.dict (default:  "model/dict")
	## - "bool" options.noprompt (default:  False)

	return parser

def main(args):
	aligner = Aligner(*args)
	aligner.read_transcript()
	aligner.check_transcript()
	aligner.check_against_dictionary()

	if check:
		return

	aligner.check_tempdir('')
	main_textgrid = praat.TextGrid()
	duration = aligner.get_duration()
	# works up to here
	aligner.align()


if __name__ == '__main__':
	# Need to convert to argparse
	parser = define_options_and_arguments()
	args = [
		wavfile,
		trsfile,
		inputfile,
		tgfile,
		dictionary_file,
		no_prompt,
		verbose,
		check,
		htktoolspath
	]
