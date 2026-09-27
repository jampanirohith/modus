from src.merger import Merger
from src.types import AlignedWord, ChunkAlignment, ChunkSpec, LRCLine, LyricDocument, SourceWord


def line(idx, ts, words):
    return LRCLine(idx, ts, " ".join(words), words=[SourceWord(idx, i, w, w) for i, w in enumerate(words)])


def chunk(idx, start, end, line_start, line_end, words):
    spec = ChunkSpec(idx, start, end, max(0, start-500), min(10000, end+500), line_start, line_end, " ".join(w.original for w in words), " ".join(w.normalized for w in words), words=words)
    return spec


def test_global_continuity_repairs_small_cross_chunk_backshift():
    doc = LyricDocument([line(0, 1000, ["ఒక"]), line(1, 2000, ["రెండు"])])
    w0 = AlignedWord(0, 0, "ఒక", "ఒక", 1000, 1300, 0.9, chunk_id=10)
    w1 = AlignedWord(1, 0, "రెండు", "రెండు", 900, 1200, 0.9, chunk_id=11)
    r = [
        ChunkAlignment(chunk(0, 1000, 1800, 0, 0, doc.lyric_lines[0].words), [w0], 0.9, 0.9, 0.9, 10, 1, 20.0),
        ChunkAlignment(chunk(1, 2000, 3000, 1, 1, doc.lyric_lines[1].words), [w1], 0.9, 0.9, 0.9, 10, 1, 20.0),
    ]
    out = Merger(200).merge(doc, r, 10000)
    assert out[1].start_ms == 1000
    assert out[1].end_ms == 1300
    assert "global_continuity_shift_+100ms" in (out[1].reason or "")


def test_interpolation_uses_global_neighbors_across_line_boundary():
    doc = LyricDocument([line(0, 1000, ["ఒక", "రెండు"]), line(1, 2000, ["మూడు"])])
    a = AlignedWord(0, 0, "ఒక", "ఒక", 1000, 1200, 0.9, chunk_id=1)
    b = AlignedWord(0, 1, "రెండు", "రెండు", None, None, None, source="missing", chunk_id=1)
    c = AlignedWord(1, 0, "మూడు", "మూడు", 1600, 1800, 0.9, chunk_id=2)
    r = [
        ChunkAlignment(chunk(0, 1000, 1400, 0, 0, doc.lyric_lines[0].words), [a, b], 0.9, 0.9, 0.9, 10, 2, 20.0),
        ChunkAlignment(chunk(1, 1400, 2400, 1, 1, doc.lyric_lines[1].words), [c], 0.9, 0.9, 0.9, 10, 1, 20.0),
    ]
    out = Merger(200).merge(doc, r, 10000)
    assert out[1].source == "interpolated"
    assert 1200 <= out[1].start_ms < out[2].start_ms


def test_large_cross_chunk_backshift_is_not_silently_sorted():
    doc = LyricDocument([line(0, 1000, ["ఒక"]), line(1, 3000, ["రెండు"])])
    w0 = AlignedWord(0, 0, "ఒక", "ఒక", 2000, 2300, 0.9, chunk_id=20)
    w1 = AlignedWord(1, 0, "రెండు", "రెండు", 100, 500, 0.9, chunk_id=21)
    r = [
        ChunkAlignment(chunk(0, 1000, 1800, 0, 0, doc.lyric_lines[0].words), [w0], 0.9, 0.9, 0.9, 10, 1, 20.0),
        ChunkAlignment(chunk(1, 3000, 4000, 1, 1, doc.lyric_lines[1].words), [w1], 0.9, 0.9, 0.9, 10, 1, 20.0),
    ]
    out = Merger(200).merge(doc, r, 10000)
    violations = Merger.global_violations(out)
    assert violations
    assert out[0].start_ms == 2000
    assert out[1].start_ms == 100


def test_blank_marker_boundary_violation_is_reported():
    doc = LyricDocument([
        line(0, 10000, ["ఒక", "రెండు"]),
        line(1, 30000, ["మూడు"]),
    ], blank_markers=[20000])
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9, chunk_id=1),
        AlignedWord(0, 1, "రెండు", "రెండు", 15000, 20500, 0.9, chunk_id=1),
        AlignedWord(1, 0, "మూడు", "మూడు", 30100, 32000, 0.9, chunk_id=2),
    ]
    violations = Merger.boundary_violations(doc, words)
    assert len(violations) == 1
    assert violations[0]["marker_ms"] == 20000
    assert violations[0]["type"] == "lyric_crosses_blank_marker"


def test_same_chunk_backward_shift_is_repaired_without_sorting():
    doc = LyricDocument([line(0, 1000, ["ఒక", "రెండు", "మూడు"])])
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 1000, 1100, 0.9, chunk_id=10),
        AlignedWord(0, 1, "రెండు", "రెండు", 1300, 1400, 0.9, chunk_id=10),
        AlignedWord(0, 2, "మూడు", "మూడు", 1250, 1350, 0.9, chunk_id=10),
    ]
    r = [ChunkAlignment(chunk(0, 1000, 2000, 0, 0, doc.lyric_lines[0].words), words, 0.9, 0.9, 0.9, 10, 3, 20.0)]
    out = Merger(200).merge(doc, r, 10000)
    assert [w.start_ms for w in out] == [1000, 1300, 1300]
    assert "global_continuity_shift_+50ms" in (out[2].reason or "")


def test_merge_does_not_mutate_chunk_results_on_repeated_calls():
    doc = LyricDocument([line(0, 1000, ["ఒక"]), line(1, 2000, ["రెండు"])])
    w0 = AlignedWord(0, 0, "ఒక", "ఒక", 1000, 1100, 0.9, chunk_id=10)
    w1 = AlignedWord(1, 0, "రెండు", "రెండు", 900, 1000, 0.9, chunk_id=11)
    r = [
        ChunkAlignment(chunk(0, 1000, 1800, 0, 0, doc.lyric_lines[0].words), [w0], 0.9, 0.9, 0.9, 10, 1, 20.0),
        ChunkAlignment(chunk(1, 2000, 3000, 1, 1, doc.lyric_lines[1].words), [w1], 0.9, 0.9, 0.9, 10, 1, 20.0),
    ]
    first = Merger(200).merge(doc, r, 10000)
    second = Merger(200).merge(doc, r, 10000)
    assert [w.start_ms for w in first] == [1000, 1000]
    assert [w.start_ms for w in second] == [1000, 1000]
    assert w1.start_ms == 900


def test_finalize_output_timing_respects_blank_markers_and_global_order():
    doc = LyricDocument([
        line(0, 10000, ["ఒక", "రెండు"]),
        line(1, 30000, ["మూడు"]),
    ], blank_markers=[20000])
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 10100, 12000, 0.9),
        AlignedWord(0, 1, "రెండు", "రెండు", 15000, 20500, 0.9),
        AlignedWord(1, 0, "మూడు", "మూడు", 19500, 22000, 0.9),
    ]
    warnings = Merger(1500).finalize_output_timing(doc, words, 60000)
    assert warnings
    assert words[0].start_ms == 10100
    assert words[1].start_ms < 20000
    assert words[1].end_ms <= 20000
    assert words[2].start_ms >= 20000
    assert words[0].start_ms <= words[1].start_ms <= words[2].start_ms
    assert Merger.global_violations(words) == []
    assert Merger.boundary_violations(doc, words) == []


def test_finalize_output_timing_repairs_large_but_renderable_regression_and_marks_reason():
    doc = LyricDocument([line(0, 10000, ["ఒక"]), line(1, 30000, ["రెండు"]), line(2, 50000, ["మూడు"])])
    words = [
        AlignedWord(0, 0, "ఒక", "ఒక", 29900, 30200, 0.8),
        AlignedWord(1, 0, "రెండు", "రెండు", 28090, 28500, 0.8),
        AlignedWord(2, 0, "మూడు", "మూడు", 50000, 50300, 0.8),
    ]
    warnings = Merger(1500).finalize_output_timing(doc, words, 60000)
    assert [w.start_ms for w in words] == sorted(w.start_ms for w in words)
    assert any("final_output_monotonic_shift_+" in (words[1].reason or "") for _ in [0])
    assert warnings
