from pathlib import Path

from src.chunker import Chunker
from src.lrc_reader import parse_lrc
from src.telugu_normalizer import NormalizationConfig, TeluguNormalizer


def test_explicit_blank_marker_closes_chunk(tmp_path: Path):
    path = tmp_path / "x.lrc"
    path.write_text(
        "[00:10.00]ఒక రెండు\n[00:20.00]మూడు నాలుగు\n[00:25.00]\n[00:50.00]ఐదు ఆరు\n",
        encoding="utf-8",
    )
    doc = parse_lrc(path)
    TeluguNormalizer(NormalizationConfig()).apply(doc.lines)
    chunks = Chunker(4000, 12000, 20000, 500, 500, 1500, 3000).build(doc, 60000)
    assert len(chunks) == 2
    assert chunks[0].logical_end_ms == 25000
    assert chunks[1].logical_start_ms == 50000
