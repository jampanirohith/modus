from src.types import SourceWord, TokenRef, TokenSpan
from src.word_builder import WordBuilder


def test_word_builder_combines_multiple_token_spans():
    words = [SourceWord(0, 0, "నువ్వే", "నువ్వే", token_start=0, token_end=2)]
    refs = [TokenRef(0, 10, 0, 0), TokenRef(1, 11, 0, 0)]
    spans = [
        TokenSpan(0, 10, 3, 5, -0.10, 0.90),
        TokenSpan(1, 11, 5, 8, -0.20, 0.80),
    ]

    result = WordBuilder().build(
        words, refs, spans,
        audio_origin_ms=1000,
        stride_ms=10.0,
        frame_limit_ms=5000,
        chunk_id=7,
    )

    assert len(result) == 1
    assert result[0].start_ms == 1030
    assert result[0].end_ms == 1080
    assert abs(result[0].score - 0.85) < 1e-12
    assert result[0].source == "aligned"
    assert result[0].chunk_id == 7


def test_word_builder_marks_unsupported_word_missing():
    words = [SourceWord(0, 0, "x", "x", token_start=0, token_end=0, supported=False)]
    result = WordBuilder().build(words, [], [], 0, 10.0, 5000)

    assert result[0].source == "missing"
    assert result[0].start_ms is None
    assert result[0].end_ms is None
    assert result[0].input_supported is False
