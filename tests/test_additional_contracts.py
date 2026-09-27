from pathlib import Path

import pytest

from src.json_manager import JSONManager
from src.lrc_generator import LRCGenerator
from src.lrc_reader import parse_lrc
from src.types import AlignedWord
from src.telugu_normalizer import NormalizationConfig, TeluguNormalizer


def test_existing_phase2_namespace_is_deep_merged(tmp_path: Path):
    manager = JSONManager()
    original = {
        "history": {"step1": {"status": "done"}},
        "phase2": {
            "outputs": {"legacy_debug_path": "keep-me"},
            "legacy_field": "keep-me-too",
        },
    }
    final = manager.add_phase2(
        original,
        {"outputs": {"mp3_sha256": "new"}, "status": "finished"},
    )
    assert final["phase2"]["outputs"]["legacy_debug_path"] == "keep-me"
    assert final["phase2"]["outputs"]["mp3_sha256"] == "new"
    assert final["phase2"]["legacy_field"] == "keep-me-too"
    assert manager.non_phase2_equal(original, final)


def test_lrc_validation_checks_rendered_timestamp(tmp_path: Path):
    source = tmp_path / "source.lrc"
    source.write_text("[00:05.00]ఒక రెండు\n", encoding="utf-8")
    document = parse_lrc(source)
    TeluguNormalizer(NormalizationConfig()).apply(document.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 5100, 5300, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 5350, 5700, 0.9),
    ]
    output = tmp_path / "final.lrc"
    generator = LRCGenerator()
    generator.generate(document, words, output)
    text = output.read_text(encoding="utf-8").replace("[00:05.10]", "[00:07.10]", 1)
    output.write_text(text, encoding="utf-8")
    with pytest.raises(RuntimeError, match="globally chronological|timestamp mismatch"):
        generator.validate(output, document, words)


def test_number_conversion_happens_before_punctuation_filtering():
    normalizer = TeluguNormalizer(
        NormalizationConfig(convert_numbers_to_telugu=True, keep_digits=False, keep_latin=False)
    )
    value, ops = normalizer.normalize_word("12,")
    assert value == "పన్నెండు"
    assert any(op["op"] == "number_to_telugu" for op in ops)
