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


def test_replace_smart_quotes():
    def test_func( testcase ):
        return transcriptprocessor.TranscriptProcessor.replace_smart_quotes(testcase)
    for test in provide_replace_smart_quotes():
        testcase = test[0]
        expected = test[1]
        assert test_func(testcase) == expected

def provide_replace_smart_quotes():
    return [
            [[u'\u2018'], ["'"]],
            [[u'\u2019'], ["'"]],
            [[u'\u201a'], ["'"]],
            [[u'\u201b'], ["'"]],
            [[u'\u201c'], ['"']],
            [[u'\u201d'], ['"']],
            [[u'\u201e'], ['"']],
            [[u'\u201f'], ['"']],
            [[u'\u2018foo'], ["'foo"]],
            [[u'foo\u2019'], ["foo'"]],
            [[u'\u201afoo'], ["'foo"]],
            [[u'foo\u201b'], ["foo'"]],
            [[u'\u201cfoo'], ['"foo']],
            [[u'foo\u201d'], ['foo"']],
            [[u'\u201efoo'], ['"foo']],
            [[u'foo\u201f'], ['foo"']],
            [
                [ u'\u2018', u'\u2019', u'\u201a', u'\u201b', u'\u201c', u'\u201d', u'\u201e', u'\u201f' ],
                ["'","'","'","'",'"','"','"','"']
            ]
        ]

def test_check_transcription_format_output():
    def test_func( testcase ):
        return transcriptprocessor.TranscriptProcessor.check_transcription_format(testcase)
    for test in provide_check_transcription_format_output():
        testcase = test[0]
        expected = test[1]
        assert test_func(testcase) == expected

def provide_check_transcription_format_output():
    return [
            [ '', ( None, '' ) ],       # Empty line should return None and original line
            [ ' '*6, ( None, ' '*6 ) ], # Line of only whitespace should return None and the original line
            [ ' \n ', (None, ' \n ') ], # Test mixed whitespace lines
            [ 'a\tb\tc\td\te', (['a','b','c','d','e'], None) ],   # Split tsv into entries, return toople of entries and None
            [ 'a\tb\tc\td\te\n', (['a','b','c','d','e'], None) ], # Trailing newline should be ignored
            [ 'a\tb\tc\td\te\t\t\t', (['a','b','c','d','e'], None) ], # Remove trailing tabs THEN split
        ]

def test_check_transcription_format_raises_value_error():
    def test_func( testcase ):
        return transcriptprocessor.TranscriptProcessor.check_transcription_format(testcase)
    for test in provide_check_transcription_format_raises_value_error():
        testcase = test[0]
        expected_error = test[1]
        with pytest.raises(expected_error):
            test_func(testcase)

def provide_check_transcription_format_raises_value_error():
    return [
            [ 'a', ValueError ],               # 1 entry
            [ 'a\tb', ValueError ],            # 2 entries
            [ 'a\tb\tc', ValueError],          # 3 entries
            [ 'a\tb\tc\td', ValueError],       # 4 entries
                                               # Skip 5 entries (not an error)
            [ 'a\tb\tc\td\te\tf', ValueError], # 6 entries
        ]

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

def provide_value_error_file():
    return [
        [   # header row is detected and deleted
            "Style\tSpeaker\tBeginning\tEnd\tDuration\nFoo\tBar\t0.0\t3.2\t3.2",
            {
                'prompt': "IDK what this is -CJB",
                'check' : '',
                'verbose': logging.DEBUG
            },
            ['Foo\tBar\t0.0\t3.2\t3.2']
        ],
        [   # test with one line 
            "Foo\tBar\t0.0\t3.2\t3.2\nTest\t1.0\t4.5\t3.5",
            {
                'prompt': "IDK what this is -CJB",
                'check' : '',
                'verbose': logging.DEBUG
            },
            ['Foo\tBar\t0.0\t3.2\t3.2\n', 'Test\t1.0\t4.5\t3.5']
        ],
        [   # test with more lines 
            "Foo\tBar\t0.0\t3.2\t3.2\nTest\t1.0\t4.5\t3.5\nTest\t1.0\t4.5\t3.5",
            {
                'prompt': "IDK what this is -CJB",
                'check' : '',
                'verbose': logging.DEBUG
            },
            ['Foo\tBar\t0.0\t3.2\t3.2\n', 'Test\t1.0\t4.5\t3.5\n', 'Test\t1.0\t4.5\t3.5']
        ]

    ]

