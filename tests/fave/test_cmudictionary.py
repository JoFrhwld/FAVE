import pytest
from fave import cmudictionary

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

def test_dictionary_init(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "cmu_dictionary.txt"
    p.write_text(CMU_EXCERPT)

    dict_obj = cmudictionary.CMU_Dictionary(p, **KWARGS)

    assert p.read_text() == CMU_EXCERPT

def test_add_dictionary_entries(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()

    p = d / "cmu_dictionary.txt"
    p.write_text(CMU_EXCERPT)

    dict_obj = cmudictionary.CMU_Dictionary(p, **KWARGS)
    # TODO the above code is duplicated from the init test
    #      so it might be better to have it commonly available

    new_word = "LINGUISTICS\tL IH0 NG G W IH1 S T IH0 K S "
    new_word_file = d / "new_word_file.dict"
    new_word_file.write_text(new_word)

    dict_obj.add_dictionary_entries(new_word_file, path=d)
    
    added_entries_file = d / dict_obj.DICT_ADDITIONS
    assert new_word.replace("\t", "  ") in added_entries_file.read_text()
