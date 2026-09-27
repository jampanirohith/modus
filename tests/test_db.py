from pathlib import Path

from src.db import Database


def test_database_reset_and_children(tmp_path: Path):
    db = Database(tmp_path / "phase2.db")
    try:
        song_id = db.upsert_song({
            "basename": "A",
            "original_mp3_path": "A.mp3",
            "original_lrc_path": "A.lrc",
            "original_json_path": "A.json",
            "original_mp3_sha256": "1",
            "original_lrc_sha256": "2",
            "original_json_sha256": "3",
        })
        db.set_song_status(song_id, pipeline_status="finished", quality_status="good")
        db.reset_for_reprocess(song_id)
        row = db.get_song(song_id)
        assert row["pipeline_status"] == "pending"
        assert row["quality_status"] == "unknown"
    finally:
        db.close()
