from __future__ import annotations
import json, re, subprocess, shutil
from pathlib import Path

def run(cmd, *, cwd=None, check=True, capture=True, env=None):
    return subprocess.run(
        cmd, cwd=cwd, check=check, text=True,
        capture_output=capture, env=env
    )

def ffmpeg_available(): return shutil.which("ffmpeg") is not None

def safe_filename(s: str) -> str:
    s = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", s).strip().rstrip(".")
    return re.sub(r"\s+", " ", s)[:180] or "untitled"

def write_json(path: Path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def read_json(path: Path): return json.loads(path.read_text(encoding="utf-8"))

def parse_timestamp(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    m = re.match(r"^(\d+):([0-5]\d)(?:\.(\d+))?$", ts)
    if not m: raise ValueError(f"Invalid LRC timestamp: {ts}")
    frac = float("0." + (m.group(3) or "0"))
    return int(m.group(1))*60 + int(m.group(2)) + frac

def format_ts(seconds: float) -> str:
    seconds = max(0.0, seconds); mm = int(seconds//60); ss = seconds-mm*60
    return f"{mm:02d}:{ss:05.2f}"
