from pathlib import Path

from src.lrc_generator import LRCGenerator
from src.lrc_reader import parse_lrc
from src.telugu_normalizer import NormalizationConfig, TeluguNormalizer
from src.types import AlignedWord


def test_word_level_lrc_generation(tmp_path: Path):
    source = tmp_path / "source.lrc"
    source.write_text("[ar:A]\n[00:05.00]ఒకే ఒక లోకం\n[00:10.00]\n", encoding="utf-8")
    doc = parse_lrc(source)
    TeluguNormalizer(NormalizationConfig()).apply(doc.lines)
    words = [
        AlignedWord(0, 0, "ఒకే", "ఒకే", 5100, 5400, 0.9),
        AlignedWord(0, 1, "ఒక", "ఒక", 5450, 5700, 0.8),
        AlignedWord(0, 2, "లోకం", "లోకం", 5750, 6200, 0.85),
    ]
    out = tmp_path / "final.lrc"
    generator = LRCGenerator()
    generator.generate(doc, words, out)
    generator.validate(out, doc, words)
    text = out.read_text(encoding="utf-8")
    assert "[00:05.10]ఒకే" in text
    assert "[00:05.45]ఒక" in text
    assert "[00:10.00]" in text


def test_lrc_validation_treats_blank_markers_as_structural_boundaries(tmp_path: Path):
    source = tmp_path / "source.lrc"
    source.write_text("[00:10.00]ఒక రెండు\n[00:20.00]\n[00:30.00]మూడు నాలుగు\n", encoding="utf-8")
    document = parse_lrc(source)
    TeluguNormalizer(NormalizationConfig()).apply(document.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 12100, 19000, 0.9),
        AlignedWord(1, 0, "మూడు", "మూడు", 30100, 32000, 0.9),
        AlignedWord(1, 1, "నాలుగు", "నాలుగు", 32100, 34000, 0.9),
    ]
    output = tmp_path / "final.lrc"
    generator = LRCGenerator()
    generator.generate(document, words, output)
    generator.validate(output, document, words)


def test_lrc_validation_allows_word_end_crossing_blank_marker_when_start_is_before(tmp_path: Path):
    source = tmp_path / "source.lrc"
    source.write_text("[00:10.00]ఒక రెండు\n[00:20.00]\n[00:30.00]మూడు నాలుగు\n", encoding="utf-8")
    document = parse_lrc(source)
    TeluguNormalizer(NormalizationConfig()).apply(document.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 12100, 20500, 0.9),
        AlignedWord(1, 0, "మూడు", "మూడు", 30100, 32000, 0.9),
        AlignedWord(1, 1, "నాలుగు", "నాలుగు", 32100, 34000, 0.9),
    ]
    output = tmp_path / "final.lrc"
    generator = LRCGenerator()
    generator.generate(document, words, output)
    generator.validate(output, document, words)


def test_lrc_validation_allows_word_end_crossing_blank_marker_when_start_is_before(tmp_path: Path):
    source = tmp_path / "source.lrc"
    source.write_text("[00:10.00]ఒక రెండు\n[00:20.00]\n[00:30.00]మూడు\n", encoding="utf-8")
    document = parse_lrc(source)
    TeluguNormalizer(NormalizationConfig()).apply(document.lines)
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 12100, 20500, 0.9),
        AlignedWord(1, 0, "మూడు", "మూడు", 30100, 32000, 0.9),
    ]
    output = tmp_path / "final.lrc"
    generator = LRCGenerator()
    generator.generate(document, words, output)
    generator.validate(output, document, words)
