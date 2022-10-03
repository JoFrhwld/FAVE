import logging
import pytest
from fave.align import transcriptprocessor
from fave import cmudictionary # We shouldn't be doing this...

# Copied from ../test_cmudictionary.py
#  which means this really should be made a fixture...
KWARGS = {
        'verbose': 1
    }

CMU_EXCERPT = """
TEST  T EH1 S T 
TEST'S  T EH1 S T S 
TESTA  T EH1 S T AH0 
TESTAMENT  T EH1 S T AH0 M AH0 N T 
TESTAMENTARY  T EH2 S T AH0 M EH1 N T ER0 IY0 
TESTED  T EH1 S T AH0 D 
TESTER  T EH1 S T ER0 
TESTERMAN  T EH1 S T ER0 M AH0 N 
TESTERS  T EH1 S T ER0 Z 
TESTERS  T EH1 S T AH0 Z 
"""

def test_read_transcription_file(tmp_path):
    tmp_directory = tmp_path / "transcripts"
    tmp_directory.mkdir()
    tmp_file = tmp_directory / "test_transcript.csv"
    dict_file = tmp_directory / "cmu.dict"
    dict_file.write_text(CMU_EXCERPT)
    cmu_dict = cmudictionary.CMU_Dictionary(dict_file, **KWARGS)
    for test_case in provide_value_error_file():
        test_text = test_case[0]
        flags = test_case[1]
        expected = test_case[2]
        tmp_file.write_text(test_text)
        tp_obj = transcriptprocessor.TranscriptProcessor(
                tmp_file,
                cmu_dict,
                **flags
            )
        tp_obj.read_transcription_file()

        assert tp_obj.lines == expected

    for test_case in provide_no_error_file():
        test_text = test_case[0]
        flags = test_case[1]
        expected = test_case[2]
        tmp_file.write_text(test_text)
        tp_obj = transcriptprocessor.TranscriptProcessor(
                tmp_file,
                cmu_dict,
                **flags
            )
        tp_obj.read_transcription_file()

        assert tp_obj.lines == expected

# this raises a ValueError, but it captured in the code
def provide_value_error_file():
    return [
        [
            "Style\tSpeaker\tBeginning\tEnd\tDuration\nFoo\tBar\t0.0\t3.2\t3.2",
            {
                'prompt': "IDK what this is -CJB",
                'check' : '',
                'verbose': logging.DEBUG
            },
            ['Style\tSpeaker\tBeginning\tEnd\tDuration\n', 'Foo\tBar\t0.0\t3.2\t3.2']
        ]
    ]

# this does not raise a ValueError
def provide_no_error_file():
    return [
        [
            "Foo\tBar\t0.0\t3.2\t3.2\nTest\t1.0\4.5\t3.5",
            {
                'prompt': "IDK what this is -CJB",
                'check' : '',
                'verbose': logging.DEBUG
            },
            ['Foo\tBar\t0.0\t3.2\t3.2\n', 'Test\t1.0\4.5\t3.5']
        ]
    ]


