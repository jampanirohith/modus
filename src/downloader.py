from __future__ import annotations
import os
import shutil
import sys
from pathlib import Path
from .utils import run

def _spotdl_command():
    # Running through the active venv is more reliable than depending on the
    # parent PowerShell PATH.
    return [sys.executable, "-m", "spotdl"]

def _spotdl_ffmpeg():
    candidates = [
        os.environ.get("SPOTDL_FFMPEG"),
        str(Path.home() / ".spotdl" / "ffmpeg.exe"),
        shutil.which("ffmpeg"),
    ]
    for value in candidates:
        if value and Path(value).is_file():
            return str(Path(value).resolve())
    return None

def _prepare_env():
    env = os.environ.copy()
    ffmpeg = _spotdl_ffmpeg()
    if ffmpeg:
        env["PATH"] = str(Path(ffmpeg).parent) + os.pathsep + env.get("PATH", "")
    return env, ffmpeg

def download_spotify(spotify_url: str, out_dir: Path, retries=3):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "spotify_audio.mp3"
    env, ffmpeg = _prepare_env()

    # SpotDL's global archive/error/skip files are deliberately disabled:
    # SQLite is the project's source of truth.
    error_log = out_dir / ".spotdl_errors.txt"
    archive = out_dir / ".spotdl_archive.txt"
    skip_file = out_dir / ".spotdl_skip"
    for p in (error_log, archive, skip_file):
        p.unlink(missing_ok=True)

    output_pattern = out_dir / "{title}.{output-ext}"
    base = _spotdl_command() + [
        "download", spotify_url,
        "--output", str(output_pattern),
        "--format", "mp3",
        "--overwrite", "force",
        "--redownload",
    ]
    if ffmpeg:
        base += ["--ffmpeg", ffmpeg]

    for attempt in range(1, retries + 1):
        try:
            for p in out_dir.glob("*.mp3"):
                if p != out:
                    p.unlink(missing_ok=True)
            out.unlink(missing_ok=True)

            result = run(base, capture=True, env=env)
            candidates = [p for p in out_dir.glob("*.mp3") if p.name != "youtube_audio.mp3"]
            if not candidates:
                stdout = (result.stdout or "").strip()
                stderr = (result.stderr or "").strip()
                detail = stderr or stdout or "no SpotDL output"
                raise RuntimeError(f"SpotDL completed but no MP3 was produced: {detail[-4000:]}")
            src = max(candidates, key=lambda p: p.stat().st_mtime)
            if src != out:
                src.replace(out)
            return out
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(f"spotdl failed after {retries} attempts: {e}") from e

    raise RuntimeError("unreachable")

def download_youtube_audio(url: str, out_dir: Path):
    out = out_dir / "youtube_audio.mp3"
    env, _ = _prepare_env()
    run([
        sys.executable, "-m", "yt_dlp",
        "--no-playlist", "-x", "--audio-format", "mp3",
        "-o", str(out), url
    ], env=env)
    if not out.exists():
        files = list(out_dir.glob("youtube_audio.*"))
        if files:
            files[0].rename(out)
    return out
