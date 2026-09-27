from src.tokenizer import ReferenceTokenizer
from src.types import SourceWord


class FakeTokenizer:
    unk_token_id = 99
    pad_token_id = 0
    bos_token_id = 101
    eos_token_id = 102

    def __call__(self, text, add_special_tokens=False, return_attention_mask=False):
        mapping = {
            "నువ్వే": [10, 11],
            "ఒకే": [12],
            "bad": [99],
        }
        return {"input_ids": mapping.get(text, [13])}


def test_reference_tokenizer_tracks_word_token_ranges():
    words = [
        SourceWord(0, 0, "నువ్వే", "నువ్వే"),
        SourceWord(0, 1, "ఒకే", "ఒకే"),
    ]
    refs = ReferenceTokenizer().build(words, FakeTokenizer())

    assert [r.token_id for r in refs] == [10, 11, 12]
    assert (words[0].token_start, words[0].token_end) == (0, 2)
    assert (words[1].token_start, words[1].token_end) == (2, 3)
    assert words[0].supported is True
    assert words[1].supported is True


def test_reference_tokenizer_marks_unknown_words_unsupported():
    words = [SourceWord(0, 0, "bad", "bad")]
    refs = ReferenceTokenizer().build(words, FakeTokenizer())

    assert refs == []
    assert words[0].supported is False
    assert words[0].token_start == 0
    assert words[0].token_end == 0
