## Praat script to get the duration of a sound file
## because Python's wave.py module does not seem to support 32-bit .wav sound files
## written by Ingrid Rosenfelder
## last modified November 18, 2011

## usage:  praat get_duration.praat soundfile

#################################################################
form Get Sound file
	sentence Sound_file_path /Users/ingrid/Programs/Forced_Alignment_Toolkit/17Nov2011_14:30:05_Barb1.wav
endform

Open long sound file... 'sound_file_path$'
duration = Get total duration
clearinfo
print 'duration'