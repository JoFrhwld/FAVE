## Praat script for getting the intensity contour for a given sound file
## written by Ingrid Rosenfelder
## last modified April 17, 2013

## Usage:  praat getIntensity.praat filename.wav

form Please specify the sound file:
  sentence audioFile
endform

filename$ = audioFile$ - ".wav" + ".Intensity"

Read from file... 'audioFile$'
duration = Get total duration
## minimum duration to get an intensity contour is 6.4 divided by the cutoff frequency
## so we need to check that our vowel meets this criterion
if duration >= 0.064
	To Intensity... 100 0.001 yes
else
	analysis_frequency = 6.4 / duration
	To Intensity... 'analysis_frequency' 0.001 yes
endif
Write to short text file... 'filename$'