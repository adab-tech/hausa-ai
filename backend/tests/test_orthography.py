from orthography import normalize_hausa_orthography

def test_normalize_hausa_orthography():
    # Test cases for hooked letters b', d', k', 'y
    assert normalize_hausa_orthography("b'aki") == "ɓaki"
    assert normalize_hausa_orthography("d'an gari") == "ɗan gari"
    assert normalize_hausa_orthography("k'asa") == "ƙasa"
    assert normalize_hausa_orthography("'yanci") == "ƴanci"
    assert normalize_hausa_orthography("y'anci") == "ƴanci"
    
    # Test standard text remains untouched
    assert normalize_hausa_orthography("Barka da zuwa") == "Barka da zuwa"
