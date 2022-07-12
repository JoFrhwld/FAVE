#!/usr/bin/env python3
# *_* coding: utf-8 *_*

"""
aligner.py contains the Aligner class and coordinates the interaction of
the other modules.
"""

__version__ = "2.0.0"
__author__ = ("Rosenfelder, Ingrid; " +  # Only code writers
              "Fruehwald, Josef; " +
              "Evanini, Keelan; " +
              "Seyfarth, Scott; " +
              "Gorman, Kyle; " +
              "Prichard, Hilary; " +
              "Yuan, Jiahong; " +
              "Brickhouse, Christian")
__email__ = "brickhouse@stanford.edu"
# should be the person who will fix bugs and make improvements
__maintainer__ = "Christian Brickhouse"
__copyright__ = "Copyright 2020, FAVE contributors"
__license__ = "GPLv3"
__status__ = "Development"  # Prototype, Development or Production
# also include contributors that wrote no code
__credits__ = ["Brandon Waldon"]

# --------------------------------------------------------------------------------

# Import built-in modules first
# followed by third-party modules
# followed by any changes to the path
# your own modules.

import os  # replace with subprocess one day
import re
import subprocess
import shutil
import time
import logging
import wave
import pkg_resources
from . import transcriptprocessor
from fave import cmudictionary
from fave import praat


class Aligner():
    """
    The Aligner class is the main user entry point to the FAVE library. It
    handles the interface between all the different modules and automates
    the process in a way that allows easy use in scripts or larger programs.
    """
    # pylint: disable=too-many-instance-attributes
    # Code debt: most of the instance attributes should be passed to functions

    STYLE = ["style", "Style", "STYLE"]
    uncertain = re.compile(r"\(\(([\*\+]?['\w]+\-?)\)\)")

    def __init__(
            self,
            wavfile,
            trsfile,
            tgfile,
            **kwargs
    ):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            format='%(name)s - %(levelname)s:%(message)s',
            level=kwargs['verbose'])

        self.count_unclear = 0
        self.count_uncertain = 0
        self.count_words = 0
        self.audio = wavfile
        default_dict = pkg_resources.resource_filename('fave.align', 'model/dict')
        if trsfile:
            self.transcript = trsfile
        else:
            self.transcript = os.path.splitext(wavfile)[0] + '.txt'
        if tgfile:
            self.textgrid = tgfile
        else:
            self.textgrid = os.path.splitext(trsfile)[0] + '.TextGrid'

        self.__config(**kwargs)

        dictionary_file = kwargs['dict'] or default_dict

        kwargs['prompt'] = False
        args = []

        self.cmu_dict = cmudictionary.CMU_Dictionary(dictionary_file, *args, **kwargs)

        if kwargs['import']:
            self.cmu_dict.add_dictionary_entries(kwargs['import'])

        self.transcript = transcriptprocessor.TranscriptProcessor(
            self.transcript,
            self.cmu_dict,
            *args,
            **kwargs)

    def __config(self,**kwargs):
        self.htktoolspath = kwargs['htktoolspath']
        self.check = kwargs['check']

    def read_transcript(self):
        """Interface with TranscriptProcessor to read a file"""
        self.transcript.read_transcription_file()

    def check_transcript(self):
        """Interface with TranscriptProcessor to check a file"""
        self.transcript.check_transcription_file()

    def check_against_dictionary(self):
        """Interface with TranscriptProcessor to check dictionary entries"""
        self.transcript.check_dictionary_entries(self.audio)

    def get_duration(self, FADIR='', PRAATPATH=''):
        """gets the overall duration of a soundfile"""
        # INPUT:  string soundfile = name of sound file
        # OUTPUT:  float duration = duration of sound file

        try:
            # calculate duration by sampling rate and number of frames
            f = wave.open(self.audio, 'r')
            sr = float(f.getframerate())
            nx = f.getnframes()
            f.close()
            duration = round((nx / sr), 3)
        except wave.Error:  # wave.py does not seem to support 32-bit .wav files???
            self.logger.debug('Script path is %s',os.path.join(
                FADIR, "praatScripts", "get_duration.praat"))
            if PRAATPATH:
                dur_command = "%s %s %s" % (PRAATPATH, os.path.join(
                    FADIR, "praatScripts", "get_duration.praat"), self.audio)
            else:
                dur_command = "praat %s %s" % (os.path.join(
                    FADIR, "praatScripts", "get_duration.praat"), self.audio)
            duration = round(
                float(
                    subprocess.Popen(
                        dur_command,
                        shell=True,
                        stdout=subprocess.PIPE).communicate()[0].strip()),
                3)

        return duration

    def align(self, tempdir='', FADIR=''):
        """Main alignment function
        """
        self.logger.info('Starting alignment')
        failed_alignment = []
        trans_lines = self.transcript.trans_lines
        all_input = self.transcript.lines
        wavfile = self.audio
        style_tier = None
        count_chunks = 0
        duration = self.get_duration()
        SOXPATH = ''
        main_textgrid = praat.TextGrid()
        if len(trans_lines) != len(all_input):
            raise ValueError('Remove empty lines from transcript')

        if FADIR:
            tmpdir = os.path.join(FADIR, 'tmp')
        else:
            tmpdir = os.path.join('.', 'tmp')
        if not os.path.isdir(tmpdir):
            self.logger.info(
                f'No temporary directory, creating one at {tmpdir}')
            os.mkdir(tmpdir)
        # start alignment of breathgroups
        for (text, line) in zip(trans_lines, all_input):
            entries = line.strip().split('\t')
            # start counting chunks (as part of the output file names) at 1
            count_chunks += 1

            # style tier?
            if (entries[0] in self.STYLE) or (entries[1] in self.STYLE):
                style_tier = self.process_style_tier(entries, style_tier)
                continue

            # normal tiers:
            speaker = entries[1].strip().replace(
                '/', ' ')  # eventually replace all \W!
            # some people forget to enter the speaker name into the second
            # field, try the first one (speaker ID) instead
            if not speaker:
                speaker = entries[0].strip()
            beg = round(float(entries[2]), 3)
            # some weird input files have the last interval exceed the duration
            # of the sound file
            end = min(round(float(entries[3]), 3), duration)
            dur = round(end - beg, 3)
            # Add logging here
            try:
                if dur < 0.05:
                    raise ValueError(
                        f"Annotation unit too short ({dur} s), cannot align.")
            except ValueError:
                continue

            # call SoX to cut the corresponding chunk out of the sound file
            chunkname_sound = "_".join([os.path.splitext(os.path.basename(wavfile))[
                0], speaker.replace(" ", "_"), "chunk", str(count_chunks)]) + ".wav"
            self.__cut_chunk(
                os.path.join(
                    tempdir,
                    chunkname_sound),
                beg,
                dur,
                SOXPATH)
            # generate name for output TextGrid
            self.logger.debug("Creating chunk textgrid")
            chunkname_textgrid = os.path.splitext(
                chunkname_sound)[0] + ".TextGrid"

            # Should add exception handling here
            # align chunk
            self.__align(
                os.path.join(
                    tempdir,
                    chunkname_sound),
                [text],
                os.path.join(
                    tempdir,
                    chunkname_textgrid),
                FADIR,
                SOXPATH,
                self.htktoolspath)
            # read TextGrid output of forced alignment
            new_textgrid = praat.TextGrid()
            new_textgrid.read(os.path.join(tempdir, chunkname_textgrid))
            # re-insert uncertain and unclear transcriptions
            new_textgrid = self.__reinsert_uncertain(new_textgrid, text)
            # change time offset of chunk
            new_textgrid.change_offset(beg)
            self.logger.debug("Offset changed by {beg} seconds.")

            # add TextGrid for new chunk to main TextGrid
            main_textgrid = self.merge_textgrids(
                main_textgrid, new_textgrid, speaker, chunkname_textgrid)

            # remove sound "chunk" and TextGrid from tempdir
            os.remove(os.path.join(tempdir, chunkname_sound))
            os.remove(os.path.join(tempdir, chunkname_textgrid))
        counts = [
            self.count_words,
            self.count_uncertain,
            self.count_unclear,
            count_chunks
        ]
        self.__cleanup(
            style_tier,
            main_textgrid,
            failed_alignment,
            duration,
            counts)

    def __cleanup(
            self,
            style_tier,
            main_textgrid,
            failed_alignment,
            duration,
            counts):
        # add style tier to main TextGrid, if applicable
        if style_tier:
            self.logger.debug('Added style tier back')
            main_textgrid.append(style_tier)

        # tidy up main TextGrid (extend durations, insert empty intervals etc.)
        try:
            main_textgrid = self.__tidyup(main_textgrid, 0, duration)
        except BaseException: # pylint: disable=W0703
            self.logger.warning("Could not tidy the TextGrid output")

        # append information on alignment failure to errorlog file
        if failed_alignment:
            self.logger.warning('Some alignments failed')
            self.__write_alignment_errors_to_log(
                self.textgrid, failed_alignment)

        # write main TextGrid to file
        try:
            main_textgrid.write(self.textgrid)
        except OSError as e:
            self.logger.error('Could not write TextGrid!')
            raise e
        else:
            self.logger.debug(
                "Successfully written TextGrid %s to file.",
                os.path.basename(self.textgrid))

        # remove temporary CMU dictionary
        try:
            os.remove(self.transcript.temp_dict_dir)
        except OSError as e:
            self.logger.error(
                'Could not remove temporary dictionary directory!')
            raise e
        else:
            self.logger.debug("Deleted temporary copy of the CMU dictionary.")

        wavfile = self.audio
        # write log file
        # This should be replaced by proper use of self.logger
        try:
            self.__write_log(
                os.path.splitext(wavfile)[0] +
                ".FAAVlog",
                wavfile,
                duration,
                counts)
        except BaseException: # pylint: disable=broad-except
            self.logger.error('Unable to write .FAAVlog')
        else:
            self.logger.debug(
                "Written log file %s.",
                os.path.basename(
                    os.path.splitext(wavfile)[0] +
                    ".FAAVlog"))

    def __cut_chunk(self, outfile, start, dur, SOXPATH):
        """uses SoX to cut a portion out of a sound file"""
        self.logger.debug(f"Cutting chunk {outfile} from {start}s to {dur}s")
        wavfile = self.audio
        if SOXPATH:
            command_cut_sound = " ".join([SOXPATH,
                                          '\"' + wavfile + '\"',
                                          '\"' + outfile + '\"',
                                          "trim",
                                          str(start),
                                          str(dur)])
        else:
            command_cut_sound = " ".join(["sox",
                                          '\"' + wavfile + '\"',
                                          '\"' + outfile + '\"',
                                          "trim",
                                          str(start),
                                          str(dur)])
        try:
            self.logger.debug(f"Cut command is:\n{command_cut_sound}")
            os.system(command_cut_sound)
            self.logger.debug(
                f"Sound chunk {outfile} successfully extracted.")
        except Exception as e:
            self.logger.error(
                f"Could not extract {outfile}!")
            raise e

    # This was the main body of Jiahong Yuan's original align.py
    def __align(self, chunk, trs_input, outfile,
                FADIR='', SOXPATH='', HTKTOOLSPATH=''):
        """calls the forced aligner"""
        # chunk = sound file to be aligned
        # trsfile = corresponding transcription file
        # outfile = output TextGrid

        self.logger.info(f"Aligning chunk {chunk}")
        self.logger.debug(f"input transcript: {trs_input}")
        self.logger.debug(f"output file: {outfile}")

        # change to Forced Alignment Toolkit directory for all the temp and
        # preparation files
        if FADIR:
            self.logger.debug(f"Changing working directory to {FADIR}")
            os.chdir(FADIR)

        self.logger.debug("Current working directory is: %s", os.getcwd())
        # derive unique identifier for tmp directory and all its file (from
        # name of the sound "chunk")
        identifier = re.sub(
            r'\W|_|chunk', '', os.path.splitext(
                os.path.split(chunk)[1])[0])
        # old names:  --> will have identifier added
        ## - "tmp"
        ## - "aligned.mlf"
        ## - "aligned.results"
        ## - "codetr.scp"
        ## - "test.scp"
        ## - "tmp.mlf"
        ## - "tmp.plp"
        ## - "tmp.wav"

        tempdir = os.path.join('.', 'tmp', identifier)
        tempwav = os.path.join('.', 'tmp', identifier, identifier + '.wav')
        tempmlf = os.path.join('.', 'tmp', identifier, identifier + '.mlf')
        tempalignedmlf = os.path.join(
            '.', 'tmp', identifier, 'aligned' + identifier + '.mlf')
        self.logger.info(f"Creating directory {tempdir}")
        try:
            os.mkdir(tempdir)
        except FileExistsError:
            self.logger.warning("Directory already exists? Reusing")
        except OSError as e:
            self.logger.critical("Could not create directory!")
            raise e
        # create working directory
        # prepare wavefile
        SR = self.__prep_wav(
            chunk,
            tempwav,
            SOXPATH)

        # prepare mlfile
        self.__prep_mlf(
            trs_input,
            tempmlf,
            identifier)

        # prepare scp files
        tempscp = os.path.join(
            '.',
            'tmp',
            identifier,
            'codetr' +
            identifier +
            '.scp')
        testscp = os.path.join(
            '.',
            'tmp',
            identifier,
            'test' +
            identifier +
            '.scp')
        tempplp = os.path.join(
            '.',
            'tmp',
            identifier,
            'tmp' +
            identifier +
            '.plp')
        with open(tempscp, 'w') as f:
            self.logger.debug(f"Writing {tempscp}")
            f.write(tempwav + ' ' + tempplp + '\n')
        with open(testscp, 'w') as f:
            self.logger.debug(f"Writing {testscp}")
            f.write(tempplp + '\n')

        try:
            # call plp.sh and align.sh
            self.logger.debug(f'Toolspath is "{HTKTOOLSPATH}"')
            if HTKTOOLSPATH:  # if absolute path to HTK Toolkit is given
                HCopy = os.path.join(HTKTOOLSPATH, 'HCopy')
                HVite = os.path.join(HTKTOOLSPATH, 'HVite')
            else:
                HCopy = 'HCopy'
                HVite = 'HVite'
            self.logger.debug(f'HCopy is "{HCopy}"')
            self.logger.debug(f'HVite is "{HVite}"')
            modelconfig = os.path.join(
                '.', 'align', 'model', str(SR), 'config')
            modelmacros = os.path.join(
                '.', 'align', 'model', str(SR), 'macros')
            modelhmmdef = os.path.join(
                '.', 'align', 'model', str(SR), 'hmmdefs')
            modelmonophones = os.path.join('.', 'align', 'model', 'monophones')
            pipedest = os.path.join(
                '.', 'tmp', identifier, 'blubbeldiblubb.txt')
            HCopyCommand = HCopy + ' -T 1 -C ' + modelconfig + \
                ' -S ' + tempscp + ' >> ' + pipedest
            HViteCommand = (HVite +
                            ' -T 1 -a -m -I ' +
                            tempmlf +
                            ' -H ' +
                            modelmacros +
                            ' -H ' +
                            modelhmmdef +
                            ' -S ' +
                            testscp +
                            ' -i ' +
                            tempalignedmlf +
                            ' -p 0.0 -s 5.0 ' +
                            self.cmu_dict.dict_dir +
                            ' ' +
                            modelmonophones +
                            ' > ' +
                            os.path.join(tempdir, identifier + '.results'))

            self.logger.debug(f'HViteCommand is "{HViteCommand}"')

            os.system(HCopyCommand)
            os.system(HViteCommand)

            # write result of alignment to TextGrid file
            self.__aligned_to_TextGrid(
                tempalignedmlf,
                outfile,
                SR)
            self.logger.debug(
                "Forced alignment called successfully for file %s",
                os.path.basename(chunk))
        except Exception as e:
            FA_error = "Error in aligning file %s:  %s." % (
                os.path.basename(chunk), e)
            # clean up temporary alignment files
            shutil.rmtree(tempdir)
            self.logger.error(FA_error)
            raise e
            # errorhandler(FA_error)

        # remove tmp directory and all files
        # This may create a race condition
        shutil.rmtree(tempdir)

    # This function is from Jiahong Yuan's align.py
    # (but adapted so that we're forcing a SR of 16,000 Hz; mono)
    def __prep_wav(self, orig_wav, out_wav, SOXPATH=''):
        """adjusts sampling rate  and number of channels of sound file to 16,000 Hz, mono."""

    # NOTE:  the wave.py module may cause problems, so we'll just copy the file
    # to 16,000 Hz mono no matter what the original file format!
    ##    f = wave.open(orig_wav, 'r')
    ##    SR = f.getframerate()
    ##    channels = f.getnchannels()
    # f.close()
    # if not (SR == 16000 and channels == 1):  ## this is changed
        SR = 16000
    # SR = 11025
        # if FAAValign is used as a CGI script, the path to SoX needs to
        # be specified explicitly
        if SOXPATH:
            os.system(
                SOXPATH +
                ' \"' +
                orig_wav +
                '\" -c 1 -r 16000 ' +
                out_wav)
        else:  # otherwise, rely on the shell to find the correct path
            os.system("sox" + ' \"' + orig_wav + '\" -c 1 -r 16000 ' + out_wav)
            #os.system("sox " + orig_wav + " -c 1 -r 11025 " + out_wav + " polyphase")
    # else:
    ##        os.system("cp -f " + '\"' + orig_wav + '\"' + " " + out_wav)

        return SR

    # This function originally is from Jiahong Yuan's align.py
    # (very much modified by Ingrid...)
    def __prep_mlf(self, transcription, mlffile, identifier):
        """writes transcription to the master label file for forced alignment"""
        # INPUT:
        # list transcription = list of list of (preprocessed) words
        # string mlffile = name of master label file
        # string identifier = unique identifier of process/sound file
        #   (can't just call everything "tmp")
        # OUTPUT:
        # none, but writes master label file to disk

        fw = open(mlffile, 'w')
        fw.write('#!MLF!#\n')
        fw.write('"*/tmp' + identifier + '.lab"\n')
        fw.write('sp\n')
        for line in transcription:
            for word in line:
                # change unclear transcription ("((xxxx))") to noise
                if word == "((xxxx))":
                    word = "{NS}"
                    self.count_unclear += 1
                # get rid of parentheses for uncertain transcription
                if self.uncertain.search(word):
                    word = self.uncertain.sub(r'\1', word)
                    self.count_uncertain += 1
                # delete initial asterisks
                if word[0] == "*":
                    word = word[1:]
                # check again that word is in CMU dictionary because of "noprompt" option,
                # or because the user might select "skip" in interactive prompt
                if word in self.cmu_dict.cmu_dict:
                    fw.write(word + '\n')
                    fw.write('sp\n')
                    self.count_words += 1
                else:
                    self.logger.warning(
                        f"Word '{word}' not in CMU dict!")
        fw.write('.\n')
        fw.close()

    # This function is from Jiahong Yuan's align.py
    # (originally called "TextGrid(infile, outfile, SR)")
    def __aligned_to_TextGrid(self, infile, outfile, SR):
        """
        writes the results of the forced alignment (file "aligned.mlf") to file
        as a Praat TextGrid file
        """

        f = open(infile, 'rU')
        lines = f.readlines()
        f.close()
        fw = open(outfile, 'w')
        j = 2
        phons = []
        wrds = []
    # try:
        while lines[j] != '.\n':
            ph = lines[j].split()[2]  # phone
            if SR == 11025:  # adjust rounding error for 11,025 Hz sampling rate
                # convert time stamps from 100ns units to seconds
                # fix overlapping intervals:  divide time stamp by ten first
                # and round!
                st = round((round(float(lines[j].split()[
                    0]) / 10.0, 0) / 1000000.0) * (11000.0 / 11025.0) + 0.0125, 3)  # start time
                en = round((round(float(lines[j].split()[
                    1]) / 10.0, 0) / 1000000.0) * (11000.0 / 11025.0) + 0.0125, 3)  # end time
            else:
                st = round(
                    round(
                        float(
                            lines[j].split()[0]) /
                        10.0,
                        0) /
                    1000000.0 +
                    0.0125,
                    3)
                en = round(
                    round(
                        float(
                            lines[j].split()[1]) /
                        10.0,
                        0) /
                    1000000.0 +
                    0.0125,
                    3)
            if st != en:  # 'sp' states between words can have zero duration
                # list of phones with start and end times in seconds
                phons.append([ph, st, en])

            if len(lines[j].split()) == 5:  # entry on word tier
                wrd = lines[j].split()[4].replace('\n', '')
                if SR == 11025:
                    st = round((round(float(lines[j].split()[
                        0]) / 10.0, 0) / 1000000.0) * (11000.0 / 11025.0) + 0.0125, 3)
                    en = round((round(float(lines[j].split()[
                        1]) / 10.0, 0) / 1000000.0) * (11000.0 / 11025.0) + 0.0125, 3)
                else:
                    st = round(
                        round(
                            float(
                                lines[j].split()[0]) /
                            10.0,
                            0) /
                        1000000.0 +
                        0.0125,
                        3)
                    en = round(
                        round(
                            float(
                                lines[j].split()[1]) /
                            10.0,
                            0) /
                        1000000.0 +
                        0.0125,
                        3)
                if st != en:
                    wrds.append([wrd, st, en])

            j += 1
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
        # write the word interval tier
        fw.write('"IntervalTier"\n')
        fw.write('"word"\n')
        fw.write(str(phons[0][1]) + '\n')
        fw.write(str(phons[-1][-1]) + '\n')
        fw.write(str(len(wrds)) + '\n')
        for k in range(len(wrds) - 1):
            fw.write(str(wrds[k][1]) + '\n')
            fw.write(str(wrds[k + 1][1]) + '\n')
            fw.write('"' + wrds[k][0] + '"' + '\n')
        fw.write(str(wrds[-1][1]) + '\n')
        fw.write(str(phons[-1][2]) + '\n')
        fw.write('"' + wrds[-1][0] + '"' + '\n')

        fw.close()

    def __reinsert_uncertain(self, tg, text):
        """compares the original transcription with the word tier of a TextGrid and
        re-inserts markup for uncertain and unclear transcriptions"""
        # INPUT:
        # praat.TextGrid tg = TextGrid that was output by the forced aligner for this "chunk"
        # list text = list of words that should correspond to entries on word
        #   tier of tg (original transcription WITH parentheses, asterisks etc.)
        # OUTPUT:
        # praat.TextGrid tg = TextGrid with original uncertain and unclear
        # transcriptions

        # forced alignment may or may not insert "sp" intervals between words
        # -> make an index of "real" words and their index on the word tier of the TextGrid first
        tgwords = []
        for (n, interval) in enumerate(tg[1]):  # word tier
            if interval.mark() not in ["sp", "SP"]:
                tgwords.append((interval.mark(), n))

        # for all "real" (non-"sp") words in transcription:
        for (n, entry) in enumerate(tgwords):
            # interval entry on word tier of FA output TextGrid
            tgword = entry[0]
            # corresponding position of that word in the TextGrid tier
            tgposition = entry[1]

            # if "noprompt" option is selected, or if the user chooses the
            # "skip" option in the interactive prompt,
            # forced alignment ignores unknown words & indexes will not match!
            # -> count how many words have been ignored up to here and
            # adjust n accordingly (n = n + ignored)
            i = 0
            while i <= n:
                # (automatically generated "in'" entries will be in dict file by now,
                # so only need to strip original word of uncertainty
                # parentheses and asterisks)
                if (self.uncertain.sub(r'\1', text[i]).lstrip(
                        '*') not in self.cmu_dict.cmu_dict and text[i] != "((xxxx))"):
                    n += 1  # !!! adjust n for every ignored word that is found !!!
                i += 1

            # original transcription contains unclear transcription:
            if text[n] == "((xxxx))":
                # corresponding interval in TextGrid must have "{NS}"
                if tgword == "{NS}" and tg[1][tgposition].mark() == "{NS}":
                    tg[1][tgposition].change_text(text[n])
                else:  # This should not happen!
                    raise ValueError(
                        "Something went wrong in the substitution" +
                        " of unclear transcriptions for the forced alignment!")

            # original transcription contains uncertain transcription:
            elif self.uncertain.search(text[n]):
                # corresponding interval in TextGrid must have transcription
                # without parentheses (and, if applicable, without asterisk)
                test = self.uncertain.sub(r'\1', text[n]).lstrip('*')
                if tgword == test and tg[1][tgposition].mark() == test:
                    tg[1][tgposition].change_text(text[n])
                else:  # This should not happen!
                    raise ValueError(
                        "Something went wrong in the substitution" +
                        " of uncertain transcriptions for the forced alignment!")

            # original transcription was asterisked word
            elif text[n][0] == "*":
                # corresponding interval in TextGrid must have transcription
                # without the asterisk
                test = text[n].lstrip('*')
                if tgword == test and tg[1][tgposition].mark() == test:
                    tg[1][tgposition].change_text(text[n])
                else:  # This should not happen!
                    raise ValueError(
                        "Something went wrong in the substitution of " +
                        " asterisked transcriptions for the forced alignment!")

        return tg

    def merge_textgrids(self, main_textgrid, new_textgrid,
                        speaker, chunkname_textgrid):
        """adds the contents of TextGrid new_textgrid to TextGrid main_textgrid"""

        for tier in new_textgrid:
            # change tier names to reflect speaker names
            # (output of FA program is "phone", "word" -> "Speaker - phone", "Speaker - word")
            tier.rename(speaker + " - " + tier.name())
            # check if tier already exists:
            for existing_tier in main_textgrid:
                if tier.name() == existing_tier.name():
                    for interval in tier:
                        existing_tier.append(interval)
                    break
            else:
                main_textgrid.append(tier)
        self.logger.debug(
            f"Successfully added {chunkname_textgrid} to main TextGrid.")
        return main_textgrid

    def process_style_tier(self, entries, style_tier=None):
        """processes entries of style tier"""
        self.logger.debug("Process style tier")
        # create new tier for style, if not already in existence
        if not style_tier:
            style_tier = praat.IntervalTier(name="style", xmin=0, xmax=0)
        # add new interval on style tier
        beg = round(float(entries[2]), 3)
        end = round(float(entries[3]), 3)
        text = entries[4].strip().upper()
        style_tier.append(praat.Interval(beg, end, text))

        return style_tier

    def __write_log(self, filename, wavfile, duration, counts):
        """writes a log file on alignment statistics"""

        count_words = counts[0]
        count_uncertain = counts[1]
        count_unclear = counts[2]
        count_chunks = counts[3]

        f = open(filename, 'w')
        t_stamp = time.asctime()
        f.write(t_stamp)
        f.write("\n\n")
        f.write(
            "Alignment statistics for file %s:\n\n" %
            os.path.basename(wavfile))

        #version = __version__

        # For development, it's helpful to know if there's anything in the repo that has been
        # changed. This block checks to see if we're in a git repo. If we are, then use git diff
        # to get the changes and write to the log file.
        #
        # code debt: this block is repeated in extractFormants.py and the code should be consolidated.
        try:
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], check=True, capture_output=True)
            try:
                check_changes = subprocess.Popen(
                    ["git", "diff", "--stat"], stdout=subprocess.PIPE)
                changes, err = check_changes.communicate() # pylint: disable=unused-variable
            except OSError:
                changes = ''

            if changes:
                f.write("Uncommitted changes when run:\n")
                f.write(changes)
        except subprocess.CalledProcessError:
            pass

        f.write("\n")
        f.write("Total number of words:\t\t\t%i\n" % count_words)
        f.write(
            "Uncertain transcriptions:\t\t%i\t(%.1f%%)\n" %
            (count_uncertain, float(count_uncertain) / float(count_words) * 100))
        f.write("Unclear passages:\t\t\t%i\t(%.1f%%)\n" %
                (count_unclear, float(count_unclear) / float(count_words) * 100))
        f.write("\n")
        f.write("Number of breath groups aligned:\t%i\n" % count_chunks)
        f.write("Duration of sound file:\t\t\t%.3f seconds\n" % duration)
        # The following is timing data that should be reinserted but is not
        #   critical to port right now.
        # pylint: disable=pointless-string-statement
        """
        f.write("Total time for alignment:\t\t%.2f seconds\n" %
                (times[-1][2] - times[1][2]))
        f.write("Total time since beginning of program:\t%.2f seconds\n\n" %
                (times[-1][2] - times[0][2]))
        f.write("->\taverage alignment duration:\t%.3f seconds per breath group\n" %
                ((times[-1][2] - times[1][2]) / count_chunks))
        f.write("->\talignment rate:\t\t\t%.3f times real time\n" %
                ((times[-1][2] - times[0][2]) / duration))
        f.write("\n\n")
        f.write("Alignment statistics:\n\n")
        f.write("Chunk\tCPU time\treal time\td(CPU)\td(time)\n")
        for i in range(len(times)):
            # first entry in "times" tuple is string already, or integer
            f.write(str(times[i][0]))  # chunk number
            f.write("\t")
            f.write(str(round(times[i][1], 3)))  # CPU time
            f.write("\t")
            f.write(time.asctime(time.localtime(times[i][2])))  # real time
            f.write("\t")
            if i > 0:  # time differences (in seconds)
                f.write(str(round(times[i][1] - times[i - 1][1], 3)))
                f.write("\t")
                f.write(str(round(times[i][2] - times[i - 1][2], 3)))
            f.write("\n")
        """
        f.close()

    def __write_alignment_errors_to_log(self, tgfile, failed_alignment):
        """appends the list of alignment failures to the error log"""

        # warn user that alignment failed for some parts of the TextGrid
        self.logger.warning("Alignment failed for some annotation units!")

        logname = os.path.splitext(tgfile)[0] + ".errorlog"
        # check whether errorlog file exists
        if os.path.exists(logname) and os.path.isfile(logname):
            errorlog = open(logname, 'a')
            errorlog.write('\n')
        else:
            errorlog = open(logname, 'w')
        errorlog.write(
            "Alignment failed for the following annotation units:  \n")
        errorlog.write("#\tbeginning\tend\tspeaker\ttext\n")
        for f in failed_alignment:
            #        try:
            errorlog.write('\t'.join(f).encode('ascii', 'replace'))
    #        except UnicodeDecodeError:
    #            errorlog.write('\t'.join(f))
            errorlog.write('\n')
        errorlog.close()
        self.logger.info(f"Alignment errors saved to file {logname}")

    def __tidyup(self, tg, beg, end):
        """extends the duration of a TextGrid and all its tiers from beg to end;
        inserts empty/"SP" intervals; checks for overlapping intervals"""

        # set overall duration of main TextGrid
        tg.change_times(beg, end)
        # set duration of all tiers and check for overlaps
        overlaps = []
        for t in tg:
            # set duration of tier from 0 to overall duration of main sound
            # file
            t.extend(beg, end)
            # insert entries for empty intervals between existing intervals
            oops = t.tidyup()
            if len(oops) != 0:
                for oo in oops:
                    overlaps.append(oo)
            self.logger.debug(f"Finished tidying up {t}")
        # write errorlog if overlapping intervals detected
        if len(overlaps) != 0:
            self.logger.warning("Overlapping intervals detected!")
            self.__write_errorlog(overlaps)

        return tg

    def __write_errorlog(self, overlaps):
        """writes log file with details on overlapping interval boundaries to file"""

        # write log file for overlapping intervals from FA
        tgfile = self.textgrid
        logname = os.path.splitext(tgfile)[0] + ".errorlog"
        errorlog = open(logname, 'w')
        errorlog.write("Overlapping intervals in file %s:  \n" % tgfile)
        for o in overlaps:
            errorlog.write(
                "Interval %s and interval %s on tier %s.\n" %
                (o[0], o[1], o[2]))
        errorlog.close()
        self.logger.info(f"Error messages saved to file {logname}")
