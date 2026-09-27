from src.lrc_reader import parse_lrc
from src.telugu_normalizer import TeluguNormalizer, NormalizationConfig
from src.types import AlignedWord
from src.validator import Validator


def test_validator_detects_global_cross_line_time_reversal(tmp_path):
    p = tmp_path / "x.lrc"
    p.write_text("[00:01.00]ఒక\n[00:02.00]రెండు\n", encoding="utf-8")
    doc = parse_lrc(p)
    TeluguNormalizer(NormalizationConfig()).apply(doc.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 1000, 1200, 0.9),
        AlignedWord(1, 0, "రెండు", "రెండు", 900, 1100, 0.9),
    ]
    metrics, reasons = Validator().validate_alignment(doc, words, 5000, 0.4, 2500)
    assert "GLOBAL_TIMESTAMP_ORDER_INVALID" in reasons
    assert metrics.continuity_violation_count == 1
    assert metrics.continuity_first_violation["current"]["start_ms"] == 900


def test_validator_rejects_lyric_crossing_explicit_blank_marker(tmp_path):
    p = tmp_path / "x.lrc"
    p.write_text("[00:10.00]ఒక రెండు\n[00:20.00]\n[00:30.00]మూడు\n", encoding="utf-8")
    doc = parse_lrc(p)
    TeluguNormalizer(NormalizationConfig()).apply(doc.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 12100, 20500, 0.9),
        AlignedWord(1, 0, "మూడు", "మూడు", 30100, 32000, 0.9),
    ]
    metrics, reasons = Validator().validate_alignment(doc, words, 60000, 0.4, 2500)
    assert "LYRIC_CROSSES_BLANK_MARKER" in reasons
    assert Validator.classify(metrics, 0) == "needs_review"
