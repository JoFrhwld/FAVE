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
## PROJECT "AUTOMATIC ALIGNMENT AND ANALYSIS OF LINGUISTIC CHANGE"            ##
## FAAValign.py                                                               ##
## written by Ingrid Rosenfelder                                              ##
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

truncated = re.compile(r'\w+\-$')                       ## truncated words
intended = re.compile(r'^\+\w+')                        ## intended word (inserted by transcribers after truncated word)
## NOTE:  earlier versions allowed uncertain/unclear transcription to use only one parenthesis,
##        but this is now back to the strict definition
##        (i.e. uncertain/unclear transcription spans MUST be enclosed in DOUBLE parentheses)
unclear = re.compile(r'\(\(\s*\)\)')                    ## unclear transcription (empty double parentheses)
start_uncertain = re.compile(r'(\(\()')                 ## beginning of uncertain transcription
end_uncertain = re.compile(r'(\)\))')                   ## end of uncertain transcription
uncertain = re.compile(r"\(\(([\*\+]?['\w]+\-?)\)\)")   ## uncertain transcription (single word)
ing = re.compile(r"IN'$")                               ## words ending in "in'"
hyphenated = re.compile(r'(\w+)-(\w+)')                 ## hyphenated words

CONSONANTS = ['B', 'CH', 'D', 'DH','F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'P', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'Y', 'Z', 'ZH']
VOWELS = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
STYLE = ["style", "Style", "STYLE"]
STYLE_ENTRIES = ["R", "N", "L", "G", "S", "K", "T", "C", "WL", "MP", "SD", "RP"]

#TEMPDIR = "temp_FA"
TEMPDIR = ""
DICT_ADDITIONS = "added_dict_entries.txt"               ## file for collecting uploaded additions to the dictionary
PRAATPATH = "/usr/local/bin/praat"                      ## this is just in case the wave module does not work (use Praat instead to determe the length of the sound file)
##PRAATPATH = "/Applications/Praat.app/Contents/MacOS/praat"  ## old setting on ingridpc.ling.upenn.edu

################################################################################

def add_dictionary_entries(infile, FADIR):
    """reads additional dictionary entries from file and adds them to the CMU dictionary"""
    ## INPUT:  string infile = name of tab-delimited file with word and Arpabet transcription entries
    ## OUTPUT:  none, but modifies CMU dictionary (cmudict)

    ## read import file
    i = open(infile, 'rU')
    lines = i.readlines()
    i.close()

    global cmudict
    add_dict = {}

    ## process entries
    for line in lines:
        try:
            word = line.strip().split('\t')[0].upper()
            trans = [check_transcription(t.strip()) for t in line.strip().split('\t')[1].replace('"', '').split(',')]
            ## (transcriptions will be converted to upper case in check_transcription)
            ## (possible to have more than one (comma-separated) transcription per word in input file)
        except IndexError:
            error = "ERROR!  Incorrect format of dictionary input file %s:  Problem with line \"%s\"." % (infile, line)
            errorhandler(error)
        ## add new entry to CMU dictionary
        if word not in cmudict and trans:
            cmudict[word] = trans
            add_dict[word] = trans
        else:   ## word might be in dict but transcriber might want to add alternative pronunciation
            for t in trans:
                if t and (t not in cmudict[word]):  ## check that new transcription is not already in dictionary  
                    cmudict[word].append(t)
                    add_dict[word] = [t]

    if options.verbose:
        print "Added all entries in file %s to CMU dictionary." % os.path.basename(infile)

    ## add new entries to the file for additional transcription entries
    ## (merge with the existing DICT_ADDITIONS file to avoid duplicates)
    if os.path.exists(os.path.join(FADIR, DICT_ADDITIONS)):  ## check whether dictionary additions file exists already
        added_already = read_dict(os.path.join(FADIR, DICT_ADDITIONS))
        new_dict = merge_dicts(added_already, add_dict)
    else:
        new_dict = add_dict
    write_dict(os.path.join(FADIR, DICT_ADDITIONS), dictionary=new_dict, mode='w')
    if options.verbose:
        print "Added new entries from file %s to file %s." % (os.path.basename(infile), DICT_ADDITIONS)


## This was the main body of Jiahong Yuan's original align.py
def align(wavfile, trs_input, outfile, FADIR='', SOXPATH='', HTKTOOLSPATH=''):
    """calls the forced aligner"""
    ## wavfile = sound file to be aligned
    ## trsfile = corresponding transcription file
    ## outfile = output TextGrid
    
    ## change to Forced Alignment Toolkit directory for all the temp and preparation files
    if FADIR:
        os.chdir(FADIR)

    ## derive unique identifier for tmp directory and all its file (from name of the sound "chunk")
    identifier = re.sub(r'\W|_|chunk', '', os.path.splitext(os.path.split(wavfile)[1])[0])
    ## old names:  --> will have identifier added
    ## - "tmp"
    ## - "aligned.mlf"
    ## - "aligned.results"
    ## - "codetr.scp"
    ## - "test.scp"
    ## - "tmp.mlf"
    ## - "tmp.plp"
    ## - "tmp.wav"
    
    # create working directory  
    os.mkdir("./tmp" + identifier)
    # prepare wavefile
    SR = prep_wav(wavfile, './tmp' + identifier + '/tmp' + identifier + '.wav', SOXPATH)

    # prepare mlfile
    prep_mlf(trs_input, './tmp' + identifier + '/tmp' + identifier + '.mlf', identifier)
 
    # prepare scp files
    fw = open('./tmp' + identifier + '/codetr' + identifier + '.scp', 'w')
    fw.write('./tmp' + identifier + '/tmp' + identifier + '.wav ./tmp' + identifier + '/tmp'+ identifier + '.plp\n')
    fw.close()
    fw = open('./tmp' + identifier + '/test' + identifier + '.scp', 'w')
    fw.write('./tmp' + identifier +'/tmp' + identifier + '.plp\n')
    fw.close()

    try:
        # call plp.sh and align.sh
        if HTKTOOLSPATH:  ## if absolute path to HTK Toolkit is given
            os.system(os.path.join(HTKTOOLSPATH, 'HCopy') + ' -T 1 -C ./model/' + str(SR) + '/config -S ./tmp' + identifier + '/codetr' + identifier + '.scp >> ./tmp' + identifier + '/blubbeldiblubb.txt')
            os.system(os.path.join(HTKTOOLSPATH, 'HVite') + ' -T 1 -a -m -I ./tmp' + identifier + '/tmp' + identifier +'.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp' + identifier + '/test' + identifier+ '.scp -i ./tmp' + identifier + '/aligned' + identifier + '.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp' + identifier + '/aligned' + identifier + '.results')
        else:  ## find path via shell
            #os.system('HCopy -T 1 -C ./model/' + str(SR) + '/config -S ./tmp/codetr.scp >> blubbeldiblubb.txt')
            #os.system('HVite -T 1 -a -m -I ./tmp/tmp.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp/test.scp -i ./tmp/aligned.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp/aligned.results')
            os.system('HCopy -T 1 -C ./model/' + str(SR) + '/config -S ./tmp' + identifier + '/codetr' + identifier + '.scp >> ./tmp' + identifier + '/blubbeldiblubb.txt')
            os.system('HVite -T 1 -a -m -I ./tmp' + identifier + '/tmp' + identifier +'.mlf -H ./model/' + str(SR) + '/macros -H ./model/' + str(SR) + '/hmmdefs  -S ./tmp' + identifier + '/test' + identifier+ '.scp -i ./tmp' + identifier + '/aligned' + identifier + '.mlf -p 0.0 -s 5.0 ' + options.dict + ' ./model/monophones > ./tmp' + identifier + '/aligned' + identifier + '.results')

        ## write result of alignment to TextGrid file
        aligned_to_TextGrid('./tmp' + identifier + '/aligned' + identifier + '.mlf', outfile, SR)
        if options.verbose:
            print "\tForced alignment called successfully for file %s." % os.path.basename(wavfile)
    except Exception, e:
        FA_error = "Error in aligning file %s:  %s." % (os.path.basename(wavfile), e)
        ## clean up temporary alignment files
        shutil.rmtree("./tmp" + identifier)
        raise Exception, FA_error
        ##errorhandler(FA_error)

    ## remove tmp directory and all files        
    shutil.rmtree("./tmp" + identifier)
    

## This function is from Jiahong Yuan's align.py
## (originally called "TextGrid(infile, outfile, SR)")
def aligned_to_TextGrid(infile, outfile, SR):
    """writes the results of the forced alignment (file "aligned.mlf") to file as a Praat TextGrid file"""
    
    f = open(infile, 'rU')
    lines = f.readlines()
    f.close()
    fw = open(outfile, 'w')
    j = 2
    phons = []
    wrds = []
##    try:
    while (lines[j] <> '.\n'):
        ph = lines[j].split()[2]  ## phone
        if (SR == 11025):  ## adjust rounding error for 11,025 Hz sampling rate
            ## convert time stamps from 100ns units to seconds
            ## fix overlapping intervals:  divide time stamp by ten first and round!
            st = round((round(float(lines[j].split()[0])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)  ## start time 
            en = round((round(float(lines[j].split()[1])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)  ## end time
        else:
            st = round(round(float(lines[j].split()[0])/10.0, 0)/1000000.0 + 0.0125, 3)
            en = round(round(float(lines[j].split()[1])/10.0, 0)/1000000.0 + 0.0125, 3)
        if (st <> en):  ## 'sp' states between words can have zero duration
            phons.append([ph, st, en])  ## list of phones with start and end times in seconds

        if (len(lines[j].split()) == 5):  ## entry on word tier
            wrd = lines[j].split()[4].replace('\n', '') 
            if (SR == 11025):
                st = round((round(float(lines[j].split()[0])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)
                en = round((round(float(lines[j].split()[1])/10.0, 0)/1000000.0)*(11000.0/11025.0) + 0.0125, 3)
            else:
                st = round(round(float(lines[j].split()[0])/10.0, 0)/1000000.0 + 0.0125, 3)
                en = round(round(float(lines[j].split()[1])/10.0, 0)/1000000.0 + 0.0125, 3)
            if (st <> en):
                wrds.append([wrd, st, en])

        j += 1
##    except Exception, e:
##        FA_error = "Error in converting times from file %s in line %d for TextGrid %s:  %s." % (os.path.basename(infile), j + 1, os.path.basename(outfile), e)
##        errorhandler(FA_error)
        
##    try:
    #write the phone interval tier
    fw.write('File type = "ooTextFile short"\n')
    fw.write('"TextGrid"\n')
    fw.write('\n')
    fw.write(str(phons[0][1]) + '\n')
    fw.write(str(phons[-1][2]) + '\n')
    fw.write('<exists>\n')
    fw.write('2\n')
    fw.write('"IntervalTier"\n')
    fw.write('"phone"\n')
    fw.write(str(phons[0][1]) + '\n')
    fw.write(str(phons[-1][-1]) + '\n')
    fw.write(str(len(phons)) + '\n')
    for k in range(len(phons)):
        fw.write(str(phons[k][1]) + '\n')
        fw.write(str(phons[k][2]) + '\n')
        fw.write('"' + phons[k][0] + '"' + '\n')
##    except Exception, e:
##        FA_error = "Error in writing phone interval tier for TextGrid %s:  %s." % (os.path.basename(outfile), e)
##        errorhandler(FA_error)
##    try:
    #write the word interval tier
    fw.write('"IntervalTier"\n')
    fw.write('"word"\n')
    fw.write(str(phons[0][1]) + '\n')
    fw.write(str(phons[-1][-1]) + '\n')
    fw.write(str(len(wrds)) + '\n')
    for k in range(len(wrds) - 1):
        fw.write(str(wrds[k][1]) + '\n')
        fw.write(str(wrds[k+1][1]) + '\n')
        fw.write('"' + wrds[k][0] + '"' + '\n')
    fw.write(str(wrds[-1][1]) + '\n')
    fw.write(str(phons[-1][2]) + '\n')
    fw.write('"' + wrds[-1][0] + '"' + '\n')
##    except Exception, e:
##        FA_error = "Error in writing phone interval tier for TextGrid %s:  %s." % (os.path.basename(outfile), e)
##        errorhandler(FA_error)

    fw.close()


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


def check_dictionary_entries(lines, wavfile):
    """checks that all words in lines have an entry in the CMU dictionary;
    if not, prompts user for Arpabet transcription and adds it to the dict file.
    If "check transcription" option is selected, writes list of unknown words to file and exits."""
    ## INPUT:  list of lines to check against CMU dictionary
    ## OUTPUT:  list newlines = list of list of words for each line (processed)
    ## - prompts user to modify CMU dictionary (cmudict) and writes updated version of CMU dictionary to file
    ## - if "check transcription" option is selected, writes list of unknown words to file and exits

    newlines = []
    unknown = {}
    ## "flag_uncertain" indicates whether we are currently inside an uncertain section of transcription
    ## (switched on and off by the beginning or end of double parentheses:  "((", "))")
    flag_uncertain = False
    last_beg_uncertain = ''
    last_end_uncertain = ''

    for line in lines:
        newwords = []
        ## get list of preprocessed words in each line
        ## ("uncertainty flag" has to be passed back and forth because uncertain passages might span more than one breathgroup)
        (words, flag_uncertain, last_beg_uncertain, last_end_uncertain) = preprocess_transcription(line.strip().upper(), flag_uncertain, last_beg_uncertain, last_end_uncertain)
        ## check each word in transcription as to whether it is in the CMU dictionary:
        ## (if "check transcription" option is not set, dict unknown will simply remain empty)
        for i, w in enumerate(words):
            if i < len(words) - 1:
                unknown = check_word(w, words[i+1], unknown, line)
            else:
                unknown = check_word(w, '', unknown, line)               ## last word in line
            ## take "clue words" out of transcription:
            if not intended.search(uncertain.sub(r'\1', w)):
                newwords.append(w)
        newlines.append(newwords)

    ## write new version of the CMU dictionary to file
    ## (do this here so that new entries to dictionary will still be saved if "check transcription" option is selected
    ## in addition to the "import transcriptions" option)
    #write_dict(options.dict)
    ## NOTE:  dict will no longer be re-written to file as people might upload all kinds of junk
    ##        Uploaded additional transcriptions will be written to a separate file instead (in add_dictionary_entries), 
    ##        to be checked manually and merged with the main dictionary at certain intervals

        
    ## write temporary version of the CMU dict to file for use in alignment
    global options  ## need to make options global because dict setting must be changed
    if not options.check:
        global temp_dict
        temp_dict = os.path.join(os.path.dirname(wavfile), '_'.join(os.path.basename(wavfile).split('_')[:2]) + "_" + "dict")
        print "temp_dict is %s." % temp_dict
        write_dict(temp_dict)
        if options.verbose:
            print "Written updated temporary version of CMU dictionary."
        ## forced alignment must use updated cmudict, not original one
        options.dict = temp_dict

    ## "CHECK TRANSCRIPTION" OPTION:
    ## write list of unknown words and suggested transcriptions for truncated words to file
    if options.check:
        write_unknown_words(unknown)            
        print "Written list of unknown words in transcription to file %s." % options.check
        if __name__ == "__main__":
            sys.exit()
            
    ## CONTINUE TO ALIGNMENT:
    else:
        ## return new transcription (list of lists of words, for each line)
        return newlines
    

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


def check_phone(p, w, i):
    """checks that a phone entered by the user is part of the Arpabet"""
    ## INPUT:
    ## string p = phone
    ## string w = word the contains the phone (normal orthographic representation)
    ## int i = index of phone in word (starts at 0)
    ## OUTPUT:
    ## string final_p or p = phone in correct format
    
    if not ((len(p) == 3 and p[-1] in ['0', '1', '2'] and p[:-1] in VOWELS) or (len(p) <= 2 and p in CONSONANTS)):
        ## check whether transcriber didn't simply forget the stress coding for vowels:
        if __name__ == "__main__":
            if len(p) == 2 and p in VOWELS:
                print "You forgot to enter the stress digit for vowel %s (at position %i) in word %s!\n" % (p, i+1, w)
                new_p = raw_input("Please re-enter vowel transcription, or type [q] to quit:  ")
            else:
                print "Unknown phone %s (at position %i) in word %s!\n" % (p, i+1, w)
                new_p = raw_input("Please correct your transcription for this phone, or type [q] to quit:  ")
            ## EMERGENCY EXIT:
            ## (to get out of the loop without having to kill the terminal) 
            if new_p in ['q', 'Q']:
                sys.exit()
            ## check new transcription:
            final_p = check_phone(new_p, w, i)
            return final_p
        else:
            error = "Unknown phone %s (at position %i) in word %s!\n" % (p, i+1, w)
            errorhandler(error)
    else:
        return p


def check_transcription(w):
    """checks that the transcription entered for a word conforms to the Arpabet style"""
    ## INPUT:  string w = phonetic transcription of a word (phones should be separated by spaces)
    ## OUTPUT:  list final_trans = list of individual phones (upper case, checked for correct format)
    
    ## convert to upper case and split into phones
    phones = w.upper().split()
    ## check that phones are separated by spaces
    ## (len(w) > 3:  transcription could just consist of a single phone!)
    if len(w) > 3 and len(phones) < 2:
        print "Something is wrong with your transcription:  %s.\n" % w
        print "Did you forget to enter spaces between individual phones?\n"
        new_trans = raw_input("Please enter new transcription:  ")
        final_trans = check_transcription(new_trans)
    else:
        final_trans = [check_phone(p, w, i) for i, p in enumerate(phones)]
        
    return final_trans

# substitute any 'smart' quotes in the input file with the corresponding
# ASCII equivalents (otherwise they will be excluded as out-of-
# vocabulary with respect to the CMU pronouncing dictionary)
# WARNING: this function currently only works for UTF-8 input
def replace_smart_quotes(all_input):
  cleaned_lines = []
  for line in all_input:
    line = line.replace(u'\u2018', "'")
    line = line.replace(u'\u2019', "'")
    line = line.replace(u'\u201a', "'")
    line = line.replace(u'\u201b', "'")
    line = line.replace(u'\u201c', '"')
    line = line.replace(u'\u201d', '"')
    line = line.replace(u'\u201e', '"')
    line = line.replace(u'\u201f', '"')
    cleaned_lines.append(line)
  return cleaned_lines

def check_transcription_file(all_input):
    """checks the format of the input transcription file and returns a list of empty lines to be deleted from the input"""
    trans_lines = []
    delete_lines = []
    for line in all_input:
        t_entries, d_line = check_transcription_format(line)
        if t_entries:
            trans_lines.append(t_entries[4])
        if d_line:
            delete_lines.append(d_line)

    return trans_lines, delete_lines    


def check_transcription_format(line):
    """checks that input format of transcription file is correct (5 tab-delimited data fields)"""
    ## INPUT:  string line = line of transcription file
    ## OUTPUT: list entries = fields in line (speaker ID and name, begin and end times, transcription text)
    ##         string line = empty transcription line to be deleted 
    
    entries = line.rstrip().split('\t')
    ## skip empty lines
    if line.strip():
        if len(entries) != 5:
            ## if there are only 4 fields per line, chances are that the annotation unit is empty and people just forgot to delete it,
            ## which is not worth aborting the program, so continue
            if len(entries) == 4:
                if options.verbose:
                    print "\tWARNING!  Empty annotation unit:  %s" % line.strip()
                return None, line
            else:
                if __name__ == "__main__":
                    print "WARNING:  Incorrect format of input file: %i entries per line." % len(entries)
                    for i in range(len(entries)):
                        print i, "\t", entries[i]
                    stop_program = raw_input("Stop program?  [y/n]")
                    if stop_program == "y":
                        sys.exit("Exiting program.")
                    elif stop_program == "n":
                        print "Continuing program."
                        return None, line
                    else:
                        sys.exit("Undecided user.  Exiting program.")
                else:
                    error = "Incorrect format of transcription file: %i entries per line in line %s." % (len(entries), line.rstrip())
                    raise Exception, error
        else:
            return entries, None
    ## empty line
    else:
        return None, line


def check_word(word, next_word='', unknown={}, line=''):
    """checks whether a given word's phonetic transcription is in the CMU dictionary;
    adds the transcription to the dictionary if not"""
    ## INPUT:                              
    ## string word = word to be checked           
    ## string next_word = following word
    ## OUTPUT:
    ## dict unknown = unknown or truncated words (needed if "check transcription" option is selected; remains empty otherwise)
    ## - modifies CMU dictionary (dict cmudict)
    global cmudict

    clue = ''

    ## dictionary entry for truncated words may exist but not be correct for the current word
    ## (check first because word will be in CMU dictionary after procedure below)
    if truncated.search(word) and word in cmudict:
        ## check whether following word is "clue" word? 
        if intended.search(next_word):
            clue = next_word
        ## do not prompt user for input if "check transcription" option is selected
        ## add truncated word together with its proposed transcription to list of unknown words
        ## (and with following "clue" word, if present)
        if options.check:
            if clue:
                unknown[word] = (cmudict[word], clue.lstrip('+'), line)
            else:
                unknown[word] = (cmudict[word], '', line)
        ## prompt user for input
        else:
            ## assume that truncated words are taken care of by the user if an import file is specified
            ## also, do not prompt user if "noprompt" option is selected
            if not (options.importfile or options.noprompt):
                print "Dictionary entry for truncated word %s is %s." % (word, cmudict[word])
                if clue:
                    print "Following word is %s." % next_word
                correct = raw_input("Is this correct?  [y/n]")
                if correct != "y":
                    transcription = prompt_user(word, clue) 
                    cmudict[word] = [transcription]
    
    elif word not in cmudict and word not in STYLE_ENTRIES:
        ## truncated words:
        if truncated.search(word):
            ## is following word "clue" word?  (starts with "+")
            if intended.search(next_word):
                clue = next_word
        ## don't do anything if word itself is a clue word
        elif intended.search(word):
            return unknown
        ## don't do anything for unclear transcriptions:
        elif word == '((xxxx))':
            return unknown
        ## uncertain transcription:
        elif start_uncertain.search(word) or end_uncertain.search(word):
            if start_uncertain.search(word) and end_uncertain.search(word):
                word = word.replace('((', '')
                word = word.replace('))', '')
                ## check if word is in dictionary without the parentheses
                check_word(word, '', unknown, line)
                return unknown
            else:  ## This should not happen!
                error= "ERROR!  Something is wrong with the transcription of word %s!" % word
                errorhandler(error)
        ## asterisked transcriptions:
        elif word and word[0] == "*":
            ## check if word is in dictionary without the asterisk
            check_word(word[1:], '', unknown, line)
            return unknown
        ## generate new entries for "-in'" words
        if ing.search(word):
            gword = ing.sub("ING", word)
            ## if word has entry/entries for corresponding "-ing" form:
            if gword in cmudict:
                for t in cmudict[gword]:
                    ## check that transcription entry ends in "- IH0 NG":
                    if t[-1] == "NG" and t[-2] == "IH0":
                        tt = t
                        tt[-1] = "N"
                        tt[-2] = "AH0"
                        if word not in cmudict:
                            cmudict[word] = [tt]
                        else:
                            cmudict[word].append(tt)
                return unknown
        ## if "check transcription" option is selected, add word to list of unknown words
        if options.check:
            if clue:
                unknown[word] = ("", clue.lstrip('+'), line)
            else:
                unknown[word] = ("", "", line)
            if options.verbose:
                print "\tUnknown word %s : %s." % (word.encode('ascii', 'replace'), line.encode('ascii', 'replace'))

        ## otherwise, promput user for Arpabet transcription of missing word
        elif not options.noprompt:
            transcription = prompt_user(word, clue)
            ## add new transcription to dictionary
            if transcription:  ## user might choose to skip this word
                cmudict[word] = [transcription]

    return unknown


def cut_chunk(wavfile, outfile, start, dur, SOXPATH):
    """uses SoX to cut a portion out of a sound file"""
    
    if SOXPATH:
        command_cut_sound = " ".join([SOXPATH, '\"' + wavfile + '\"', '\"' + outfile + '\"', "trim", str(start), str(dur)])
        ## ("sox <original sound file> "<new sound chunk>" trim <start of selection (in sec)> <duration of selection (in sec)>")
        ## (put file paths into quotation marks to accomodate special characters (spaces, parantheses etc.))
    else:
        command_cut_sound = " ".join(["sox", '\"' + wavfile + '\"', '\"' + outfile + '\"', "trim", str(start), str(dur)])
    try:
        os.system(command_cut_sound)
        if options.verbose:
            print "\tSound chunk %s successfully extracted." % (outfile) #os.path.basename(outfile)
    except Exception, e:
        sound_error = "Error in extracting sound chunk %s:  %s." % (os.path.basename(outfile), e)
        errorhandler(sound_error)


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
    parser.add_option('-c', '--check', help=check_help, metavar='FILENAME')                        ## required argument FILENAME
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


def delete_empty_lines(delete_lines, all_input):
    """deletes empty lines from the original input (this is important to match up the original and processed transcriptions later)"""

    #print "Lines to be deleted (%s):  %s" % (len(delete_lines), delete_lines)
    #print "Original input is %d lines long." % len(all_input)
    p = 0  ## use pointer to mark current position in original input (to speed things up a little)
    for dline in delete_lines:
        d = dline.split('\t')
        ## reset pointer p if we have run unsuccessfully through the whole input for the previous dline
        if p == len(all_input):
            p = 0
        while p < len(all_input):
            ## go through the original input lines until we find the line to delete
            o = all_input[p].split('\t')
            ## first four fields (speaker ID, speaker name, beginning and end of annotation unit) have to agree
            ## otherwise, the problem is not caused by an empty annotation unit
            ## and the program should terminate with an error
            ## (not o[0].strip():  delete completely empty lines as well!)
            if (len(o) >= 4 and (o[0] == d[0]) and (o[1] == d[1]) and (o[2] == d[2]) and (o[3] == d[3])) or not o[0].strip():
                all_input.pop(p)
                ## get out of the loop
                break
            p += 1

    #print "Input is now %d lines long." % len(all_input)
    if options.verbose:
        print "Deleted empty lines from original transcription file."

    return all_input
        

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
##    and ("audio/x-wav" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##                                           or "audio/x-wav" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
##    ## NOTE:  "file" options:
##    ##          -b      brief (no filenames appended)
##    ##          -i/-I   outputs MIME file types (capital letter or not different for different versions)
        return True
    else:
        return False


def is_text(f):
    """checks whether a file is a .txt text file"""
    
    if f.lower().endswith('.txt'):
## NOTE:  This is the old version of the file check using a call to 'file' via the command line
##    and ("text/plain" in subprocess.Popen('file -bi "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
##                                           or "text/plain" in subprocess.Popen('file -bI "%s"' % f, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()):
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
#     """creates a temporary directory for all alignment "chunks";
#     warns against overwriting existing files if applicable"""
    
#     ## check whether directory already exists and has files in it
#     if os.path.isdir(tempdir):
#         contents = os.listdir(tempdir)
#         if len(contents) != 0 and not options.noprompt:
#             print "WARNING!  Directory %s already exists and is non-empty!" % tempdir
#             print "(Files in directory:  %s )" % contents
#             overwrite = raw_input("Overwrite and continue?  [y/n]")
#             if overwrite == "y":
#                 ## delete contents of tempdir
#                 for item in contents:
#                     os.remove(os.path.join(tempdir, item))
#             elif overwrite == "n":
#                 sys.exit("Exiting program.")
#             else:
#                 sys.exit("Undecided user.  Exiting program.")
#     else:
#         os.mkdir(tempdir)


def check_tempdir(tempdir):
    """checks that the temporary directory for all alignment "chunks" is empty"""
    
    ## (NOTE:  This is a modified version of make_tempdir)
    ## check whether directory already exists and has files in it
    if os.path.isdir(tempdir):
        contents = os.listdir(tempdir)
        if len(contents) != 0 and not options.noprompt:
            print "WARNING!  Directory %s is non-empty!" % tempdir
            print "(Files in directory:  %s )" % contents
            overwrite = raw_input("Overwrite and continue?  [y/n]")
            if overwrite == "y":
                ## delete contents of tempdir
                for item in contents:
                    os.remove(os.path.join(tempdir, item))
            elif overwrite == "n":
                sys.exit("Exiting program.")
            else:
                sys.exit("Undecided user.  Exiting program.")


def mark_time(index):
    """generates a time stamp entry in global list times[]"""
    
    cpu_time = time.clock()
    real_time = time.time()
    times.append((index, cpu_time, real_time))


def merge_dicts(d1, d2):
    """merges two versions of the CMU pronouncing dictionary"""
    ## for each word, each transcription in d2, check if present in d1
    for word in d2:
        ## if no entry in d1, add entire entry 
        if word not in d1:
            d1[word] = d2[word]
        ## if entry in d1, check whether additional transcription variants need to be added
        else:
            for t in d2[word]:
                if t not in d1[word]:
                    d1[word].append(t)
    return d1


def merge_textgrids(main_textgrid, new_textgrid, speaker, chunkname_textgrid):
    """adds the contents of TextGrid new_textgrid to TextGrid main_textgrid"""
    
    for tier in new_textgrid:
        ## change tier names to reflect speaker names
        ## (output of FA program is "phone", "word" -> "Speaker - phone", "Speaker - word")
        tier.rename(speaker + " - " + tier.name())
        ## check if tier already exists:
        exists = False
        for existing_tier in main_textgrid:
            if tier.name() == existing_tier.name():
                exists = True
                break   ## need this so existing_tier retains its value!!!
        if exists:
            for interval in tier:
                existing_tier.append(interval)
        else:
            main_textgrid.append(tier)
    if options.verbose:
        print "\tSuccessfully added", chunkname_textgrid, "to main TextGrid."
        
    return main_textgrid


def preprocess_transcription(line, flag_uncertain, last_beg_uncertain, last_end_uncertain):
    """preprocesses transcription input for CMU dictionary lookup and forced alignment"""
    ## INPUT:  string line = line of orthographic transcription
    ## OUTPUT:  list words = list of individual words in transcription
    
    original_line = line

    ## make "high school" into one word (for /ay0/ raising)
    line = line.replace('high school', 'highschool')
    
    ## make beginning and end of uncertain transcription spans into separate words
    line = start_uncertain.sub(r' (( ', line)
    line = end_uncertain.sub(r' )) ', line)   
    ## correct a common transcription error (one dash instead of two)
    line = line.replace(' - ', ' -- ')
    ## delete punctuation marks
    for p in [',', '.', ':', ';', '!', '?', '"', '%', '--']:
        line = line.replace(p, ' ')
    ## delete initial apostrophes
    line = re.compile(r"(\s|^)'\b").sub(" ", line)
    ## delete variable coding for consonant cluster reduction
    line = re.compile(r"\d\w(\w)?").sub(" ", line)
    ## replace unclear transcription markup (empty parentheses):
    line = unclear.sub('((xxxx))', line)
    ## correct another transcription error:  truncation dash outside of double parentheses will become a word
    line = line.replace(' - ', '')

    ## split hyphenated words (but keep truncated words as they are!)
    ## NOTE:  This also affects the interjections "huh-uh", "uh-huh" and "uh-oh".
    ## However, should work fine just aligning individual components.
    line = hyphenated.sub(r'\1 \2', line)
    line = hyphenated.sub(r'\1 \2', line)   ## do this twice for words like "daughter-in-law"
    
    ## split line into words:
    words = line.split()

    ## add uncertainty parentheses around every word individually
    newwords = []
    for word in words:
        if word == "((":        ## beginning of uncertain transcription span
            if not flag_uncertain:
                flag_uncertain = True
                last_beg_uncertain = original_line
            else:   ## This should not happen! (but might because of transcription errors)
                error = "ERROR!  Beginning of uncertain transcription span detected twice in a row:  %s.  Please close the the opening double parenthesis in line %s." % (original_line, last_beg_uncertain)
                errorhandler(error)
        elif word == "))":      ## end of uncertain transcription span
            if flag_uncertain:
                flag_uncertain = False
                last_end_uncertain = original_line
            else:   ## Again, this should not happen! (but might because of transcription errors)
                error = "ERROR!  End of uncertain transcription span detected twice in a row:  No opening double parentheses for line %s." % original_line
                errorhandler(error)
        else:  ## process words
            if flag_uncertain:
                newwords.append("((" + word + "))")
            else:
                newwords.append(word)

    return (newwords, flag_uncertain, last_beg_uncertain, last_end_uncertain)


## This function originally is from Jiahong Yuan's align.py
## (very much modified by Ingrid...)
def prep_mlf(transcription, mlffile, identifier):
    """writes transcription to the master label file for forced alignment"""
    ## INPUT:
    ## list transcription = list of list of (preprocessed) words
    ## string mlffile = name of master label file
    ## string identifier = unique identifier of process/sound file (can't just call everything "tmp")
    ## OUTPUT:
    ## none, but writes master label file to disk
    
    fw = open(mlffile, 'w')
    fw.write('#!MLF!#\n')
    fw.write('"*/tmp' + identifier + '.lab"\n')
    fw.write('sp\n')
    for line in transcription:
        for word in line:
            ## change unclear transcription ("((xxxx))") to noise
            if word == "((xxxx))":
                word = "{NS}"
                global count_unclear
                count_unclear += 1
            ## get rid of parentheses for uncertain transcription
            if uncertain.search(word):
                word = uncertain.sub(r'\1', word)
                global count_uncertain
                count_uncertain += 1
            ## delete initial asterisks
            if word[0] == "*":
                word = word[1:]
            ## check again that word is in CMU dictionary because of "noprompt" option,
            ## or because the user might select "skip" in interactive prompt
            if word in cmudict:
                fw.write(word + '\n')
                fw.write('sp\n')
                global count_words
                count_words += 1
            else:
                print "\tWarning!  Word %s not in CMU dict!!!" % word.encode('ascii', 'replace')
    fw.write('.\n')
    fw.close()


## This function is from Jiahong Yuan's align.py
## (but adapted so that we're forcing a SR of 16,000 Hz; mono)
def prep_wav(orig_wav, out_wav, SOXPATH=''):
    """adjusts sampling rate  and number of channels of sound file to 16,000 Hz, mono."""

## NOTE:  the wave.py module may cause problems, so we'll just copy the file to 16,000 Hz mono no matter what the original file format!
##    f = wave.open(orig_wav, 'r')
##    SR = f.getframerate()
##    channels = f.getnchannels()
##    f.close()
##    if not (SR == 16000 and channels == 1):  ## this is changed
    SR = 16000
##        #SR = 11025
    if SOXPATH:  ## if FAAValign is used as a CGI script, the path to SoX needs to be specified explicitly
        os.system(SOXPATH + ' \"' + orig_wav + '\" -c 1 -r 16000 ' + out_wav)
    else:        ## otherwise, rely on the shell to find the correct path
        os.system("sox" + ' \"' + orig_wav + '\" -c 1 -r 16000 ' + out_wav)            
        #os.system("sox " + orig_wav + " -c 1 -r 11025 " + out_wav + " polyphase")
##    else:
##        os.system("cp -f " + '\"' + orig_wav + '\"' + " " + out_wav)

    return SR


def process_style_tier(entries, style_tier=None):
    """processes entries of style tier"""
    
    ## create new tier for style, if not already in existence
    if not style_tier:
        style_tier = praat.IntervalTier(name="style", xmin=0, xmax=0)
        if options.verbose:
            print "Processing style tier."
    ## add new interval on style tier
    beg = round(float(entries[2]), 3)
    end = round(float(entries[3]), 3)
    text = entries[4].strip().upper()
    ## check that entry on style tier has one of the allowed values
##    if text in STYLE_ENTRIES:
    style_tier.append(praat.Interval(beg, end, text))
##    else:
##        error = "ERROR!  Invalid entry on style tier:  %s (interval %.2f - %.2f)" % (text, beg, end)
##        errorhandler(error)
        
    return style_tier


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


## This function is from Keelan Evanini's cmu.py:
def read_dict(f):
    """reads the CMU dictionary (or any other dictionary in the same format) and returns it as dictionary object,
    allowing multiple pronunciations for the same word"""
    ## INPUT:  string f = name/path of dictionary file
    ## OUTPUT:  dict cmudict = dictionary of word - (list of) transcription(s) pairs
    ## (where each transcription consists of a list of phones)
    
    dictfile = open(f, 'rU')
    lines = dictfile.readlines()
    cmudict = {}
    pat = re.compile('  *')                ## two spaces separating CMU dict entries
    for line in lines:
        line = line.rstrip()
        line = re.sub(pat, ' ', line)      ## reduce all spaces to one
        word = line.split(' ')[0]          ## orthographic transcription
        phones = line.split(' ')[1:]       ## phonemic transcription
        if word not in cmudict:
            cmudict[word] = [phones]       ## phonemic transcriptions represented as list of lists of phones
        else:
            if phones not in cmudict[word]:
                cmudict[word].append(phones)   ## add alternative pronunciation to list of pronunciations
    dictfile.close()
    
    ## check that cmudict has entries
    if len(cmudict) == 0:
        print "WARNING!  Dictionary is empty."
    if options.verbose:
        print "Read dictionary from file %s." % f
        
    return cmudict


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


def reinsert_uncertain(tg, text):
    """compares the original transcription with the word tier of a TextGrid and
    re-inserts markup for uncertain and unclear transcriptions"""
    ## INPUT:
    ## praat.TextGrid tg = TextGrid that was output by the forced aligner for this "chunk"
    ## list text = list of words that should correspond to entries on word tier of tg (original transcription WITH parentheses, asterisks etc.)
    ## OUTPUT:
    ## praat.TextGrid tg = TextGrid with original uncertain and unclear transcriptions

    ## forced alignment may or may not insert "sp" intervals between words
    ## -> make an index of "real" words and their index on the word tier of the TextGrid first
    tgwords = []
    for (n, interval) in enumerate(tg[1]):  ## word tier
        if interval.mark() not in ["sp", "SP"]:
            tgwords.append((interval.mark(), n))
##    print "\t\ttgwords:  ", tgwords
##    print "\t\ttext:  ", text

    ## for all "real" (non-"sp") words in transcription:
    for (n, entry) in enumerate(tgwords):
        tgword = entry[0]               ## interval entry on word tier of FA output TextGrid
        tgposition = entry[1]           ## corresponding position of that word in the TextGrid tier
        
        ## if "noprompt" option is selected, or if the user chooses the "skip" option in the interactive prompt,
        ## forced alignment ignores unknown words & indexes will not match!
        ## -> count how many words have been ignored up to here and adjust n accordingly (n = n + ignored)
        i = 0
        while i <= n:
            ## (automatically generated "in'" entries will be in dict file by now,
            ## so only need to strip original word of uncertainty parentheses and asterisks)
            if (uncertain.sub(r'\1', text[i]).lstrip('*') not in cmudict and text[i] != "((xxxx))"):
                n += 1  ## !!! adjust n for every ignored word that is found !!!
            i += 1
        
        ## original transcription contains unclear transcription:
        if text[n] == "((xxxx))":
            ## corresponding interval in TextGrid must have "{NS}"
            if tgword == "{NS}" and tg[1][tgposition].mark() == "{NS}":
                tg[1][tgposition].change_text(text[n])
            else:  ## This should not happen!
                error = "ERROR!  Something went wrong in the substitution of unclear transcriptions for the forced alignment!"
                errorhandler(error)

        ## original transcription contains uncertain transcription:
        elif uncertain.search(text[n]):
            ## corresponding interval in TextGrid must have transcription without parentheses (and, if applicable, without asterisk)
            if tgword == uncertain.sub(r'\1', text[n]).lstrip('*') and tg[1][tgposition].mark() == uncertain.sub(r'\1', text[n]).lstrip('*'):
                tg[1][tgposition].change_text(text[n])
            else:  ## This should not happen!
                error = "ERROR!  Something went wrong in the substitution of uncertain transcriptions for the forced alignment!"
                errorhandler(error)

        ## original transcription was asterisked word
        elif text[n][0] == "*":
            ## corresponding interval in TextGrid must have transcription without the asterisk
            if tgword == text[n].lstrip('*') and tg[1][tgposition].mark() == text[n].lstrip('*'):
                tg[1][tgposition].change_text(text[n])
            else:  ## This should not happen!
                 error = "ERROR!  Something went wrong in the substitution of asterisked transcriptions for the forced alignment!"
                 errorhandler(error)
            
    return tg


# def remove_tempdir(tempdir):
#     """removes the temporary directory and all its contents"""
    
#     for item in os.listdir(tempdir):
#         os.remove(os.path.join(tempdir, item))
#     os.removedirs(tempdir)
#     os.remove("blubbeldiblubb.txt")

 
def replace_extension(filename, newextension):
    """chops off the extension from the filename and replaces it with newextension"""

    return os.path.splitext(filename)[0] + newextension


# def empty_tempdir(tempdir):
#     """empties the temporary directory of all files"""
#     ## (NOTE:  This is a modified version of remove_tempdir)
    
#     for item in os.listdir(tempdir):
#         os.remove(os.path.join(tempdir, item))
#     os.remove("blubbeldiblubb.txt")


def tidyup(tg, beg, end, tgfile):
    """extends the duration of a TextGrid and all its tiers from beg to end;
    inserts empty/"SP" intervals; checks for overlapping intervals"""
    
    ## set overall duration of main TextGrid
    tg.change_times(beg, end)
    ## set duration of all tiers and check for overlaps
    overlaps = []
    for t in tg:
        ## set duration of tier from 0 to overall duration of main sound file
        t.extend(beg, end)
        ## insert entries for empty intervals between existing intervals
        oops = t.tidyup()
        if len(oops) != 0:
            for oo in oops:
                overlaps.append(oo)
        if options.verbose:
            print "Finished tidying up %s." % t
    ## write errorlog if overlapping intervals detected
    if len(overlaps) != 0:
        print "WARNING!  Overlapping intervals detected!"
        write_errorlog(overlaps, tgfile)
        
    return tg


def write_dict(f, dictionary="cmudict", mode='w'):
    """writes the new version of the CMU dictionary (or any other dictionary) to file"""
    
    ## default functionality is to write the CMU pronunciation dictionary back to file,
    ## but other dictionaries or parts of dictionaries can also be written/appended
    if dictionary == "cmudict":
        dictionary = cmudict
#        print "dictionary is cmudict"
    out = open(f, mode)
    ## sort dictionary before writing to file
    s = dictionary.keys()
    s.sort()
    for w in s:
        ## make a separate entry for each pronunciation in case of alternative entries
        for t in dictionary[w]:
            if t:
                out.write(w + '  ')     ## two spaces separating CMU dict entries from phonetic transcriptions
                for p in t:
                    out.write(p + ' ')  ## list of phones, separated by spaces
                out.write('\n')         ## end of entry line
    out.close()
#    if options.verbose:
#        print "Written pronunciation dictionary to file."
   

def write_errorlog(overlaps, tgfile):
    """writes log file with details on overlapping interval boundaries to file"""
    
    ## write log file for overlapping intervals from FA
    logname = os.path.splitext(tgfile)[0] + ".errorlog"
    errorlog = open(logname, 'w')
    errorlog.write("Overlapping intervals in file %s:  \n" % tgfile)
    for o in overlaps:
        errorlog.write("Interval %s and interval %s on tier %s.\n" % (o[0], o[1], o[2]))
    errorlog.close()
    print "Error messages saved to file %s." % logname


def write_alignment_errors_to_log(tgfile, failed_alignment):
    """appends the list of alignment failures to the error log"""

    ## warn user that alignment failed for some parts of the TextGrid
    print "WARNING!  Alignment failed for some annotation units!"

    logname = os.path.splitext(tgfile)[0] + ".errorlog"
    ## check whether errorlog file exists
    if os.path.exists(logname) and os.path.isfile(logname):
        errorlog = open(logname, 'a')
        errorlog.write('\n')
    else:
        errorlog = open(logname, 'w')
    errorlog.write("Alignment failed for the following annotation units:  \n")
    errorlog.write("#\tbeginning\tend\tspeaker\ttext\n")
    for f in failed_alignment:
#        try:
        errorlog.write('\t'.join(f).encode('ascii', 'replace'))
#        except UnicodeDecodeError:
#            errorlog.write('\t'.join(f))
        errorlog.write('\n')
    errorlog.close()
    print "Alignment errors saved to file %s." % logname
    

def write_log(filename, wavfile, duration):
    """writes a log file on alignment statistics"""
    
    f = open(filename, 'w')
    t_stamp = time.asctime()
    f.write(t_stamp)
    f.write("\n\n")
    f.write("Alignment statistics for file %s:\n\n" % os.path.basename(wavfile))

    try:
        check_version = subprocess.Popen(["git","describe", "--tags"], stdout = subprocess.PIPE)
        version,err = check_version.communicate()
        version = version.rstrip()
    except OSError:
        version = None

    if version:
        f.write("version info from Git: %s"%version)
        f.write("\n")
    else:
        f.write("Not using Git version control. Version info unavailable.\n")
        f.write("Consider installing Git (http://git-scm.com/).\
         and cloning this repository from GitHub with: \n \
         git clone git@github.com:JoFrhwld/FAVE.git")
        f.write("\n")

    try:
        check_changes = subprocess.Popen(["git", "diff", "--stat"], stdout = subprocess.PIPE)
        changes, err = check_changes.communicate()
    except OSError:
        changes = None

    if changes:
        f.write("Uncommitted changes when run:\n")
        f.write(changes)
        
    f.write("\n")
    f.write("Total number of words:\t\t\t%i\n" % count_words)
    f.write("Uncertain transcriptions:\t\t%i\t(%.1f%%)\n" % (count_uncertain, float(count_uncertain)/float(count_words)*100))
    f.write("Unclear passages:\t\t\t%i\t(%.1f%%)\n" % (count_unclear, float(count_unclear)/float(count_words)*100))
    f.write("\n")
    f.write("Number of breath groups aligned:\t%i\n" % count_chunks)
    f.write("Duration of sound file:\t\t\t%.3f seconds\n" % duration)
    f.write("Total time for alignment:\t\t%.2f seconds\n" % (times[-1][2] - times[1][2]))
    f.write("Total time since beginning of program:\t%.2f seconds\n\n" % (times[-1][2] - times[0][2]))
    f.write("->\taverage alignment duration:\t%.3f seconds per breath group\n" % ((times[-1][2] - times[1][2])/count_chunks))
    f.write("->\talignment rate:\t\t\t%.3f times real time\n" % ((times[-1][2] - times[0][2])/duration))
    f.write("\n\n")
    f.write("Alignment statistics:\n\n")
    f.write("Chunk\tCPU time\treal time\td(CPU)\td(time)\n")
    for i in range(len(times)):
        ## first entry in "times" tuple is string already, or integer
        f.write(str(times[i][0]))                               ## chunk number
        f.write("\t")
        f.write(str(round(times[i][1], 3)))                     ## CPU time
        f.write("\t")
        f.write(time.asctime(time.localtime(times[i][2])))      ## real time
        f.write("\t")        
        if i > 0:                                               ## time differences (in seconds)
            f.write(str(round(times[i][1] - times[i-1][1], 3)))
            f.write("\t")
            f.write(str(round(times[i][2] - times[i-1][2], 3)))
        f.write("\n")
    f.close()

    return t_stamp


def write_unknown_words(unknown):
    """writes the list of unknown words to file"""
        ## try ASCII output first:
    try:
        out = open(options.check, 'w')
        write_words(out, unknown)
    except UnicodeEncodeError:  ## encountered some non-ASCII characters
        out = codecs.open(options.check, 'w', 'utf-16')
        write_words(out, unknown)


def write_words(out, unknown):
    """writes unknown words to file (in a specified encoding)"""

    for w in unknown:
        out.write(w)
        if unknown[w]:
            out.write('\t')
            ## put suggested transcription(s) for truncated word into second column, if present:
            if unknown[w][0]:
                 out.write(','.join([' '.join(i) for i in unknown[w][0]]))
            out.write('\t')
            ## put following clue word in third column, if present:
            if unknown[w][1]:
                out.write(unknown[w][1])
            ## put line in fourth column:
            out.write('\t' + unknown[w][2])
        out.write('\n')
    out.close()



################################################################################
## This used to be the main program...                                        ##
## Now it's wrapped in a function so we can import the code                   ##
## without supplying the options and arguments via the command line           ##
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
    ## NOTE:    If the "check transcription" option is selected,
    ##          the list of unknown words will be output to file
    ##          -> END OF PROGRAM!!!
    if options.verbose:  
        print "Checking dictionary entries for all words in the input transcription..."
    trans_lines = check_dictionary_entries(trans_lines, wavfile)
    if not trans_lines and not __name__ == "__main__":
        return

    ## make temporary directory for sound "chunks" and output of FA program
    #make_tempdir(tempdir)
    check_tempdir(tempdir)
    #if options.verbose:  
    #    print "Checked temporary directory %s." % tempdir

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

    ## start alignment of breathgroups
    for (text, line) in zip(trans_lines, all_input):

        entries = line.strip().split('\t')
        ## start counting chunks (as part of the output file names) at 1
        count_chunks += 1

        ## style tier?
        if (entries[0] in STYLE) or (entries[1] in STYLE):
            style_tier = process_style_tier(entries, style_tier)
            continue

        ## normal tiers:
        speaker = entries[1].strip().encode('ascii', 'ignore').replace('/', ' ')  ## eventually replace all \W!
        if not speaker:  ## some people forget to enter the speaker name into the second field, try the first one (speaker ID) instead
            speaker = entries[0].strip()
        beg = round(float(entries[2]), 3)
        end = min(round(float(entries[3]), 3), duration)  ## some weird input files have the last interval exceed the duration of the sound file
        dur = round(end - beg, 3)
        if options.verbose:
            try:
                print "Processing %s -- chunk %i:  %s" % (speaker, count_chunks, " ".join(text))
            except (UnicodeDecodeError, UnicodeEncodeError):  ## I will never get these encoding issues...  %-(
                print "Processing %s -- chunk %i:  %s" % (speaker, count_chunks, " ".join(text).encode('ascii', 'replace'))

        if dur < 0.05:
            print "\tWARNING!  Annotation unit too short (%s s) - no alignment possible." % dur
            print "\tSkipping alignment for annotation unit ", " ".join(text).encode('ascii', 'replace')
            continue
            
        ## call SoX to cut the corresponding chunk out of the sound file
        chunkname_sound = "_".join([os.path.splitext(os.path.basename(wavfile))[0], speaker.replace(" ", "_"), "chunk", str(count_chunks)]) + ".wav"
        cut_chunk(wavfile, os.path.join(tempdir, chunkname_sound), beg, dur, SOXPATH)
        ## generate name for output TextGrid
        chunkname_textgrid = os.path.splitext(chunkname_sound)[0] + ".TextGrid"
                    
        ## align chunk
        try:
            align(os.path.join(tempdir, chunkname_sound), [text], os.path.join(tempdir, chunkname_textgrid), FADIR, SOXPATH, HTKTOOLSPATH)
        except Exception, e:
            try:
                print "\tERROR!  Alignment failed for chunk %i (speaker %s, text %s)." % (count_chunks, speaker, " ".join(text))
            except (UnicodeDecodeError, UnicodeEncodeError): 
                print "\tERROR!  Alignment failed for chunk %i (speaker %s, text %s)." % (count_chunks, speaker, " ".join(text).encode('ascii', 'replace'))
            print "\n", traceback.format_exc(), "\n"
            print "\tContinuing alignment..."
            failed_alignment.append([str(count_chunks), str(beg), str(end), speaker, " ".join(text)])
            ## remove temp files
            os.remove(os.path.join(tempdir, chunkname_sound))
            os.remove(os.path.join(tempdir, chunkname_textgrid))
            continue
           
        ## read TextGrid output of forced alignment
        new_textgrid = praat.TextGrid()
        new_textgrid.read(os.path.join(tempdir, chunkname_textgrid))
        ## re-insert uncertain and unclear transcriptions
        new_textgrid = reinsert_uncertain(new_textgrid, text)
        ## change time offset of chunk
        new_textgrid.change_offset(beg)
        if options.verbose:
            print "\tOffset changed by %s seconds." % beg

        ## add TextGrid for new chunk to main TextGrid
        main_textgrid = merge_textgrids(main_textgrid, new_textgrid, speaker, chunkname_textgrid)

        ## remove sound "chunk" and TextGrid from tempdir
        os.remove(os.path.join(tempdir, chunkname_sound))
        os.remove(os.path.join(tempdir, chunkname_textgrid))
        
        mark_time(str(count_chunks))
        
    ## add style tier to main TextGrid, if applicable
    if style_tier:
        main_textgrid.append(style_tier)

    ## tidy up main TextGrid (extend durations, insert empty intervals etc.)
    main_textgrid = tidyup(main_textgrid, 0, duration, tgfile)

    ## append information on alignment failure to errorlog file
    if failed_alignment:
        write_alignment_errors_to_log(tgfile, failed_alignment)

    ## write main TextGrid to file
    main_textgrid.write(tgfile)
    if options.verbose:
        print "Successfully written TextGrid %s to file." % os.path.basename(tgfile)

    ## delete temporary transcription files and "chunk" sound file/temp directory
    #remove_tempdir(tempdir)
    #empty_tempdir(tempdir)
    #os.remove("blubbeldiblubb.txt")
    ## NOTE:  no longer needed because sound chunks and corresponding TextGrids are cleaned up in the loop
    ##        also, might delete sound chunks from other processes running in parallel!!!

    ## remove temporary CMU dictionary
    os.remove(temp_dict)
    if options.verbose:
        print "Deleted temporary copy of the CMU dictionary."
    
    ## write log file
    t_stamp = write_log(os.path.splitext(wavfile)[0] + ".FAAVlog", wavfile, duration)
    if options.verbose:
        print "Written log file %s." % os.path.basename(os.path.splitext(wavfile)[0] + ".FAAVlog")


################################################################################
## MAIN PROGRAM STARTS HERE                                                   ##
################################################################################

if __name__ == '__main__':
        
    ## get input/output file names and options
    parser = define_options_and_arguments()
    (opts, args) = parser.parse_args()

    FAAValign(opts, args)


