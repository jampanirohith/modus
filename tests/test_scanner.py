from pathlib import Path

from src.scanner import Scanner


def test_discover_requires_same_basename_sidecars(tmp_path: Path):
    (tmp_path / "A.mp3").write_bytes(b"")
    (tmp_path / "A.lrc").write_text("[00:01.00]x\n", encoding="utf-8")
    (tmp_path / "B.mp3").write_bytes(b"")
    (tmp_path / "B.json").write_text("{}", encoding="utf-8")
    scanner = Scanner.__new__(Scanner)
    packages = scanner.discover(tmp_path)
    assert len(packages) == 0
    assert {x.issue for x in scanner.issues} == {"MISSING_JSON", "MISSING_LRC"}
