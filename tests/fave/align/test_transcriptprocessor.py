import pytest
from fave.align import transcriptprocessor

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
