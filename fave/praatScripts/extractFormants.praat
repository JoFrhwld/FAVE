# Usage:  praat extractFormants.praat filename.wav nFormants maxFormant windowSize preEmphasis method

form Get_arguments
  word audioFile
  integer nFormants
  integer maxFormant
  real windowSize
  integer preEmphasis
  word method
endform

# get the number of characters in the file name
flen = length(audioFile$)
# cut off the final '.wav' (or other three-character file extension) to get the full path of the .Formant file that we will create
path$ = left$ (audioFile$, flen-4)

Read from file... 'audioFile$'

if method$ == "all"
  To Formant (keep all)... 0.001 'nFormants' 'maxFormant' 'windowSize' 'preEmphasis'
#  To Formant (keep all)... 0.0 'nFormants' 'maxFormant' 'windowSize' 'preEmphasis'
# by default, use the Burg method
else
  To Formant (burg)... 0.001 'nFormants' 'maxFormant' 'windowSize' 'preEmphasis'
#  To Formant (burg)... 0.0 'nFormants' 'maxFormant' 'windowSize' 'preEmphasis'
endif

#echo writing Praat Formant file: 'path$'.Formant
Write to short text file... 'path$'.Formant