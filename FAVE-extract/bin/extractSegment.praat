form Get_arguments
  text infile
  text outfile
  real beg
  real end
endform

Read from file... 'infile$'
wavname$ = selected$ ("Sound")
Extract part... 'beg' 'end' Rectangular 1 no
Write to WAV file... 'outfile$'
echo extracted audio segment from 'beg' sec to 'end' sec as 'outfile$'
