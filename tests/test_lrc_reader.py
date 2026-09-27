from pathlib import Path

from src.lrc_reader import blank_intervals, format_timestamp, parse_lrc, parse_timestamp


def test_timestamp_roundtrip():
    value = "[01:02.34]"
    assert parse_timestamp(value) == 62340
    assert format_timestamp(62340) == value


def test_parse_multiple_timestamps_and_blank_markers(tmp_path: Path):
    path = tmp_path / "song.lrc"
    path.write_text("[ar:Artist]\n[00:10.00][00:12.50]పాట ఒకటి\n[00:20.00]\n[00:40.00]పాట రెండు\n", encoding="utf-8")
    doc = parse_lrc(path)
    assert [x.timestamp_ms for x in doc.lyric_lines] == [10000, 12500, 40000]
    assert doc.blank_markers == [20000]
    assert blank_intervals(doc, 60000) == [(20000, 40000)]
