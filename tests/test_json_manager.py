from pathlib import Path

from src.json_manager import JSONManager


def test_json_preservation_and_self_hash(tmp_path: Path):
    manager = JSONManager()
    original = {"title": "X", "history": {"a": 1}, "phase2_old": "not-owned"}
    phase2 = {
        "pipeline_version": "1.0.0",
        "config_hash": "abc",
        "outputs": {"mp3_sha256": "123", "lrc_sha256": "456"},
    }
    final = manager.add_phase2(original, phase2)
    path = tmp_path / "x.json"
    manager.write(path, final)
    loaded = manager.load(path)
    assert manager.validate_content_hash(loaded)
    assert manager.non_phase2_equal(original, loaded)
    assert loaded["history"] == {"a": 1}
    assert loaded["phase2"]["outputs"]["mp3_sha256"] == "123"
