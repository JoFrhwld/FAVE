#!/usr/bin/env python

"""
Usage:  (python) FAAValign.py [options] soundfile.wav [transcription.txt] [output.TextGrid]

Aligns a sound file with the corresponding transcription text. The
transcription text is split into annotation breath groups, which are fed
individually as "chunks" to the forced aligner. All output is concatenated
into a single Praat TextGrid file.

INPUT:
- sound file
- tab-delimited text file with the following columns:
	first column:   speaker ID
	second column:  speaker name
	third column:   beginning of breath group (in seconds)
	fourth column:  end of breath group (in seconds)
	fifth column:   transcribed text
(If no name is specified for the transcription file, it will be assumed to
have the same name as the sound file, plus ".txt" extension.)

OUTPUT:
- Praat TextGrid file with orthographic and phonemic transcription tiers for
each speaker (If no name is specified, it will be given same name as the sound
file, plus ".TextGrid" extension.)


Options:

--version ("version"):

	Prints the program's version string and exits.

-h, --help ("help):

	Show this help message and exits.

-c [filename], --check=[filename] ("check transcription"):

	Checks whether phonetic transcriptions for all words in the transcription file can be found in the
	CMU Pronouncing Dictionary (file "dict").  Returns a list of unknown words.

-i [filename], --import=[filename] ("import dictionary entries"):

	Adds a list of unknown words and their corresponding phonetic transcriptions to the CMU Pronouncing
	Dictionary prior to alignment.  User will be prompted interactively for the transcriptions of any
	remaining unknown words.  File must be tab-separated plain text file.

-v, --verbose ("verbose"):

	Detailed output on status of dictionary check and alignment progress.

-d [filename], --dict=[filename] ("dictionary"):

	Specifies the name of the file containing the pronunciation dictionary.  Default file is "/model/dict".

-n, --noprompt ("no prompt"):

-t HTKTOOLSPATH, --htktoolspath=HTKTOOLSPATH
	Specifies the path to the HTKTools directory where the HTK executable files are located.  If not specified, the user's path will be searched for the location of the executable.

	User is not prompted for the transcription of words not in the dictionary, or truncated words.  Unknown words are ignored by the aligner.
"""

################################################################################
## PROJECT "AUTOMATIC ALIGNMENT AND ANALYSIS OF LINGUISTIC CHANGE"			##
## FAAValign.py															   ##
## written by Ingrid Rosenfelder											  ##
################################################################################

import os
import sys
import shutil
import re
import wave
import optparse
import time
import praat
import subprocess
import traceback
import codecs
import subprocess
import string





#TEMPDIR = "temp_FA"
TEMPDIR = ""
PRAATPATH = "/usr/local/bin/praat"					  ## this is just in case the wave module does not work (use Praat instead to determe the length of the sound file)
##PRAATPATH = "/Applications/Praat.app/Contents/MacOS/praat"  ## old setting on ingridpc.ling.upenn.edu

################################################################################







def check_arguments(args):
	"""returns sound file, transcription file and output TextGrid file from positional arguments from command line"""

	## no or too many positional arguments
	if len(args) == 0 or len(args) > 3:
		error = "ERROR!  Incorrect number of arguments: %s" % args
		errorhandler(error)
	## sound file must be present and first positional argument
	## EXCEPT when checking for unknown words!
	elif is_sound(args[0]) or options.check:
		## case A:  sound file is first argument
		if is_sound(args[0]):
			wavfile = check_file(args[0])
			if len(args) == 1:  ## only sound file given
				trsfile = check_file(replace_extension(wavfile, ".txt"))
				tgfile = replace_extension(wavfile, ".TextGrid")
			elif len(args) == 2:
				if is_text(args[1]):  ## sound file and transcription file given
					trsfile = check_file(args[1])
					tgfile = replace_extension(wavfile, ".TextGrid")
				elif is_TextGrid(args[1]):  ## sound file and output TextGrid given
					tgfile = args[1]
					trsfile = check_file(replace_extension(wavfile, ".txt"))  ## transcription file name must match sound file
			elif len(args) == 3:  ## all three arguments given
				trsfile = check_file(args[1])
				tgfile = args[2]
			else:  ## this should not happen
				error = "Something weird is going on here..."
				errorhandler(error)
		## case B:  unknown words check, no sound file
		elif options.check:
			wavfile = ''
			## if run from the command line, the first file must now be the transcription file
			## if run as a module, the first argument will be an empty string for the sound file, and the transcription file is still the second argument
			if (__name__ == "__main__" and is_text(args[0])) or (__name__ != "__main__" and is_text(args[1])):
				if (__name__ == "__main__" and is_text(args[0])):
					trsfile = check_file(args[0])
				elif (__name__ != "__main__" and is_text(args[1])):
					trsfile = check_file(args[1])
				tgfile = replace_extension(trsfile, ".TextGrid")  ## need to have a name for the TextGrid for the name of the outputlog (renamed from original name of the TextGrid later)
			else:
				error = "ERROR!  Transcription file needed for unknown words check."
				if __name__ == "__main__":
					print error
					sys.exit(parser.print_usage())
				else:
					raise Exception, error
		else:  ## this should not happen
			error = "Something weird is going on here!!!"
			errorhandler(error)
	else:  ## no sound file, and not checking unknown words
		error = "ERROR!  First argument to program must be sound file."
		if __name__ == "__main__":
			print error
			sys.exit(parser.print_usage())
		else:
			raise Exception, error

	return (wavfile, trsfile, tgfile)

def check_file(path):
	"""checks whether a file exists at a given location and is a data file"""

	if os.path.exists(path) and os.path.isfile(path):
		return path
	else:
		if __name__ == "__main__":
			print "ERROR!  File %s could not be found!" % path
			print "Current working directory is %s." % os.getcwd()
			newpath = raw_input("Please enter correct name or path for file, or type [q] to quit:  ")
			## emergency exit from recursion loop:
			if newpath in ['q', 'Q']:
				sys.exit("Program interrupted by user.")
			else:
				## re-check...
				checked_path = check_file(newpath)
			return checked_path
		else:
			error = "ERROR!  File %s could not be found!" % path
			errorhandler(error)








def errorhandler(errormessage):
	"""handles the error depending on whether the file is run as a standalone or as an imported module"""

	if __name__ == "__main__":  ## file run as standalone program
		sys.exit(errormessage)
	else:  ## run as imported module from somewhere else -> propagate exception
		raise Exception, errormessage


def format_option_text(text):
	"""re-formats usage, description and epiloge strings for the OptionParser
	so that they do not get mangled by optparse's textwrap"""
	## NOTE:  This is a (pretty ugly) hack to (partially) preserve newline characters
	## in the description strings for the OptionParser.
	## "textwrap" appears to preserve (non-initial) spaces, so all lines containing newlines
	## are padded with spaces until they reach the length of 80 characters,
	## which is the width to which "textwrap" formats the description text.

	lines = text.split('\n')
	newlines = ''
	for line in lines:
		## pad remainder of line with spaces
		n, m = divmod(len(line), 80)
		if m != 0:
			line += (' ' * (80 - m))
		newlines += line

	return newlines


def get_duration(soundfile, FADIR=''):
	"""gets the overall duration of a soundfile"""
	## INPUT:  string soundfile = name of sound file
	## OUTPUT:  float duration = duration of sound file

	try:
		## calculate duration by sampling rate and number of frames
		f = wave.open(soundfile, 'r')
		sr = float(f.getframerate())
		nx = f.getnframes()
		f.close()
		duration = round((nx / sr), 3)
	except wave.Error:  ## wave.py does not seem to support 32-bit .wav files???
		if PRAATPATH:
			dur_command = "%s %s %s" % (PRAATPATH, os.path.join(FADIR, "get_duration.praat"), soundfile)
		else:
			dur_command = "praat %s %s" % (os.path.join(FADIR, "get_duration.praat"), soundfile)
		duration = round(float(subprocess.Popen(dur_command, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()), 3)

	return duration


def is_sound(f):
	"""checks whether a file is a .wav sound file"""

	if f.lower().endswith('.wav'):
## NOTE:  This is the old version of the file check using a call to 'file' via the command line
##	and ("audio/x-wav" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##										   or "audio/x-wav" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
##	## NOTE:  "file" options:
##	##		  -b	  brief (no filenames appended)
##	##		  -i/-I   outputs MIME file types (capital letter or not different for different versions)
		return True
	else:
		return False


def is_text(f):
	"""checks whether a file is a .txt text file"""

	if f.lower().endswith('.txt'):
## NOTE:  This is the old version of the file check using a call to 'file' via the command line
##	and ("text/plain" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##										   or "text/plain" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
		return True
	else:
		return False


def is_TextGrid(f):
	"""checks whether a file is a .TextGrid file"""

	if re.search("\.TextGrid$", f):  ## do not test the actual file type because file does not yet exist at this point!
		return True
	else:
		return False


# def make_tempdir(tempdir):
#	 """creates a temporary directory for all alignment "chunks";
#	 warns against overwriting existing files if applicable"""

#	 ## check whether directory already exists and has files in it
#	 if os.path.isdir(tempdir):
#		 contents = os.listdir(tempdir)
#		 if len(contents) != 0 and not options.noprompt:
#			 print "WARNING!  Directory %s already exists and is non-empty!" % tempdir
#			 print "(Files in directory:  %s )" % contents
#			 overwrite = raw_input("Overwrite and continue?  [y/n]")
#			 if overwrite == "y":
#				 ## delete contents of tempdir
#				 for item in contents:
#					 os.remove(os.path.join(tempdir, item))
#			 elif overwrite == "n":
#				 sys.exit("Exiting program.")
#			 else:
#				 sys.exit("Undecided user.  Exiting program.")
#	 else:
#		 os.mkdir(tempdir)





def mark_time(index):
	"""generates a time stamp entry in global list times[]"""

	cpu_time = time.clock()
	real_time = time.time()
	times.append((index, cpu_time, real_time))







def prompt_user(word, clue=''):
	"""asks the user for the Arpabet transcription of a word"""
	## INPUT:
	## string word = word to be transcribed
	## string clue = following word (optional)
	## OUTPUT:
	## list checked_trans = transcription in Arpabet format (list of phones)

	print "Please enter the Arpabet transcription of word %s, or enter [s] to skip." % word
	if clue:
		print "(Following word is %s.)" % clue
	print "\n"
	trans = raw_input()
	if trans != "s":
		checked_trans = check_transcription(trans)
		return checked_trans
	else:
		return None

def read_transcription_file(trsfile):
	"""reads the transcription file in either ASCII or UTF-16 encoding, returns a list of lines in the file"""

	try:  ## try UTF-16 encoding first
		t = codecs.open(trsfile, 'rU', encoding='utf-16')
		print "Encoding is UTF-16!"
		lines = t.readlines()
	except UnicodeError:
		try:  ## then UTF-8...
			t = codecs.open(trsfile, 'rU', encoding='utf-8')
			print "Encoding is UTF-8!"
			lines = t.readlines()
			lines = replace_smart_quotes(lines)
		except UnicodeError:
			try:  ## then Windows encoding...
				t = codecs.open(trsfile, 'rU', encoding='windows-1252')
				print "Encoding is Windows-1252!"
				lines = t.readlines()
			except UnicodeError:
				t = open(trsfile, 'rU')
				print "Encoding is ASCII!"
				lines = t.readlines()

	return lines





# def remove_tempdir(tempdir):
#	 """removes the temporary directory and all its contents"""

#	 for item in os.listdir(tempdir):
#		 os.remove(os.path.join(tempdir, item))
#	 os.removedirs(tempdir)
#	 os.remove("blubbeldiblubb.txt")


def replace_extension(filename, newextension):
	"""chops off the extension from the filename and replaces it with newextension"""

	return os.path.splitext(filename)[0] + newextension


# def empty_tempdir(tempdir):
#	 """empties the temporary directory of all files"""
#	 ## (NOTE:  This is a modified version of remove_tempdir)

#	 for item in os.listdir(tempdir):
#		 os.remove(os.path.join(tempdir, item))
#	 os.remove("blubbeldiblubb.txt")












################################################################################
## This used to be the main program...										##
## Now it's wrapped in a function so we can import the code				   ##
## without supplying the options and arguments via the command line		   ##
################################################################################


def FAAValign(opts, args, FADIR='', SOXPATH=''):
	"""runs the forced aligner for the arguments given"""

	tempdir = os.path.join(FADIR, TEMPDIR)

	## need to make options global (now this is no longer the main program...)
	global options
	options = opts

	## get start time of program
	global times
	times = []
	mark_time("start")

	## positional arguments should be soundfile, transcription file, and TextGrid file
	## (checking that the options are valid is handled by the parser)
	(wavfile, trsfile, tgfile) = check_arguments(args)
	## (returned values are the full paths!)

	## read CMU dictionary
	## (default location is "/model/dict", unless specified otherwise via the "--dict" option)
	global cmudict
	cmudict = read_dict(os.path.join(FADIR, options.dict))

	## add transcriptions from import file to dictionary, if applicable
	if options.importfile:
		add_dictionary_entries(options.importfile, FADIR)

	## read transcription file
	all_input = read_transcription_file(trsfile)
	if options.verbose:
		print "Read transcription file %s." % os.path.basename(trsfile)

	## initialize counters
	global count_chunks
	global count_words
	global count_uncertain
	global count_unclear
	global style_tier

	count_chunks = 0
	count_words = 0
	count_uncertain = 0
	count_unclear = 0
	style_tier = None
	failed_alignment = []

	HTKTOOLSPATH = options.htktoolspath

	## check correct format of input file; get list of transcription lines
	## (this function skips empty annotation units -> lines to be deleted)
	if options.verbose:
		print "Checking format of input transcription file..."
	trans_lines, delete_lines = check_transcription_file(all_input)

	## check that all words in the transcription columen of trsfile are in the CMU dictionary
	## -> get list of words for each line, preprocessed and without "clue words"
	## NOTE:	If the "check transcription" option is selected,
	##		  the list of unknown words will be output to file
	##		  -> END OF PROGRAM!!!
	if options.verbose:
		print "Checking dictionary entries for all words in the input transcription..."
	trans_lines = check_dictionary_entries(trans_lines, wavfile)
	if not trans_lines and not __name__ == "__main__":
		return

	## make temporary directory for sound "chunks" and output of FA program
	#make_tempdir(tempdir)
	check_tempdir(tempdir)
	#if options.verbose:
	#	print "Checked temporary directory %s." % tempdir

	## generate main TextGrid and get overall duration of main sound file
	main_textgrid = praat.TextGrid()
	if options.verbose:
		print "Generated main TextGrid."
	duration = get_duration(wavfile, FADIR)
	if options.verbose:
		print "Duration of sound file:  %f seconds." % duration

	## delete empty lines from array of original transcription lines
	all_input2 = delete_empty_lines(delete_lines, all_input)
	## check length of data arrays before zipping them:
	if not (len(trans_lines) == len(all_input)):
		error = "ERROR!  Length of input data lines (%s) does not match length of transcription lines (%s).  Please delete empty transcription intervals." % (len(all_input), len(trans_lines))
		errorhandler(error)

	mark_time("prelim")






################################################################################
## MAIN PROGRAM STARTS HERE												   ##
################################################################################

if __name__ == '__main__':

	## get input/output file names and options
	parser = define_options_and_arguments()
	(opts, args) = parser.parse_args()

	FAAValign(opts, args)
