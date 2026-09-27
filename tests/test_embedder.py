from pathlib import Path
import shutil
import subprocess

import pytest
from mutagen.id3 import ID3, TIT2, TXXX
from mutagen.mp3 import MP3

from src.embedder import MP3Embedder, PHASE2_SYLT_KEY
from src.types import AlignedWord


def test_embedder_preserves_existing_tag_frames(tmp_path: Path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not installed")

    wav = tmp_path / "in.wav"
    mp3 = tmp_path / "in.mp3"
    staged = tmp_path / "out.mp3"
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-ar", "44100", "-ac", "1", str(wav)
    ], check=True)
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "5", str(mp3)
    ], check=True)

    source = MP3(mp3, ID3=ID3)
    source.add_tags() if source.tags is None else None
    source.tags.add(TIT2(encoding=3, text=["Test title"]))
    source.tags.add(TXXX(encoding=3, desc="PreserveMe", text=["keep"]))
    source.save(v2_version=3)

    words = [
        AlignedWord(0, 0, "పాట", "పాట", 100, 400, 0.9),
        AlignedWord(0, 1, "ఒకటి", "ఒకటి", 450, 800, 0.8),
    ]
    embedder = MP3Embedder()
    before = embedder.embed(mp3, staged, words)
    embedder.validate(staged, before, 2)
    tags = MP3(staged, ID3=ID3).tags
    assert tags is not None
    assert "TIT2" in tags
    assert "TXXX:PreserveMe" in tags
    assert PHASE2_SYLT_KEY in tags
