from src.telugu_normalizer import NormalizationConfig, TeluguNormalizer


def test_number_conversion_and_punctuation():
    normalizer = TeluguNormalizer(
        NormalizationConfig(convert_numbers_to_telugu=True, keep_digits=False, keep_latin=False)
    )
    value, ops = normalizer.normalize_word("12,")
    assert value == "పన్నెండు"
    assert any(op["op"] == "number_to_telugu" for op in ops)


def test_original_text_is_not_modified():
    normalizer = TeluguNormalizer(NormalizationConfig())
    value, _ = normalizer.normalize_word("పాటే,")
    assert value == "పాటే"
