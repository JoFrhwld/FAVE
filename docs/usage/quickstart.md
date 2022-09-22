# Quickstart guide to using FAVE 2.0

> 1. Install FAVE and its dependencies according to {doc}`the directions <installation>`.
>
> 2. Download the `FAAValign.py` and `extractFormants.py` scripts.
>
> 3. Check your transcription for out-of-dictionary words
>
>    ```{code-block} console
>    :caption: Check for out-of-dictionary words
>
>    python3 FAAValign.py --check unknown_words.txt AudioFile.wav TranscriptionFile.txt OutputAlignment.TextGrid
>    ```
>
> 4. Open `unknown_words.txt` and create a transcription for each word listed.
>
> 5. Align your audio and transcripts including your new transcriptions:
>
>    ```{code-block} console
>    :caption: Begin forced alignment
>
>    python3 FAAValign.py --import custom_dictionary.txt AudioFile.wav TranscriptionFile.txt OutputAlignment.TextGrid
>    ```
>
> 6. Extract formant data using the default settings:
>
>    ```{code-block} console
>    :caption: Extract formant data
>
>    python3 extractFormants.py AudioFile.wav Alignment.TextGrid OutputFileName.tsv
>    ```
