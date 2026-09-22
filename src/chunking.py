from __future__ import annotations
from pathlib import Path
from .lyrics import parse_sync
from .utils import write_json
import math
import soundfile as sf

def build_segments(reference_lrc: Path, max_sec=20, min_sec=4, pause_cut=1.5):
    lines = parse_sync(reference_lrc.read_text(encoding="utf-8"))
    if not lines:
        raise ValueError("reference_sync.lrc contains no timed lyric lines")
    groups, cur = [], []
    for i, line in enumerate(lines):
        cur.append(line)
        gap = (lines[i + 1][0] - line[0]) if i + 1 < len(lines) else 2.0
        duration = line[0] - cur[0][0]
        should = gap > pause_cut or duration >= max_sec
        if should:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    merged = []
    for g in groups:
        if (
            merged
            and (g[-1][0] - g[0][0] + 0.5) < min_sec
            and (g[-1][0] - merged[-1][-1][0] + 0.5) <= max_sec
        ):
            merged[-1].extend(g)
        else:
            merged.append(g)
    return merged

def dynamic_bounds(groups, duration, large_gap=3, large_buf=2, med_buf=1, tiny_buf=.3):
    bounds = []
    for i, g in enumerate(groups):
        start = g[0][0]
        end = groups[i + 1][0][0] if i + 1 < len(groups) else duration
        prev_gap = start - (groups[i - 1][-1][0] if i else start) if i else 999
        next_gap = end - g[-1][0] if i + 1 < len(groups) else max(0, duration - g[-1][0])
        gap = min(prev_gap if i else next_gap, next_gap)
        if gap > large_gap:
            buf = large_buf
        elif gap >= 1.5:
            buf = med_buf
        else:
            buf = tiny_buf
        left_space = max(0, start - (groups[i - 1][-1][0] if i else 0))
        right_space = max(0, end - g[-1][0])
        left = min(buf, left_space / 2 if i else buf)
        right = min(buf, right_space / 2 if i + 1 < len(groups) else buf)
        a = max(0, start - left)
        b = min(duration, end + right)
        if bounds:
            a = max(a, bounds[-1][1])
        bounds.append((a, b))
    return bounds

def _wav_duration(path: Path):
    info = sf.info(str(path))
    return float(info.frames / info.samplerate)

def _export_slice(audio_path: Path, start: float, end: float, out: Path):
    with sf.SoundFile(str(audio_path), "r") as f:
        sr = f.samplerate
        a = max(0, int(round(start * sr)))
        b = min(len(f), int(round(end * sr)))
        if b <= a:
            raise ValueError(f"Empty audio slice: {start:.3f}-{end:.3f}s")
        f.seek(a)
        data = f.read(b - a, dtype="float32", always_2d=False)
    sf.write(str(out), data, sr, subtype="PCM_16")

def make_chunks(vocals: Path, reference: Path, work: Path, cfg):
    duration = _wav_duration(vocals)
    groups = build_segments(
        reference,
        float(cfg.processing["max_segment_seconds"]),
        float(cfg.processing["min_segment_seconds"]),
        float(cfg.processing["pause_cut_seconds"]),
    )
    bounds = dynamic_bounds(
        groups, duration,
        float(cfg.processing["large_gap_seconds"]),
        float(cfg.processing["large_buffer_seconds"]),
        float(cfg.processing["medium_buffer_seconds"]),
        float(cfg.processing["tiny_buffer_seconds"]),
    )
    mapping = []
    for i, (g, (a, b)) in enumerate(zip(groups, bounds), 1):
        p = work / f"chunk_{i:02d}.wav"
        _export_slice(vocals, a, b, p)
        mapping.append({
            "chunk": i, "path": p.name, "start": a, "end": b,
            "lines": [{"time": x[0], "text": x[1]} for x in g],
        })
    write_json(work / "chunk_mapping.json", mapping)
    return mapping

def make_plain_chunks(vocals: Path, clean_text: str, work: Path, cfg):
    duration = _wav_duration(vocals)
    words = clean_text.split()
    if not words:
        raise ValueError("Plain lyric text is empty")
    n = max(1, int(math.ceil(duration / float(cfg.processing["max_segment_seconds"]))))
    groups = []
    for i in range(n):
        a, b = (len(words) * i) // n, (len(words) * (i + 1)) // n
        if b > a:
            groups.append(words[a:b])

    mapping = []
    for i, g in enumerate(groups, 1):
        a = duration * (i - 1) / len(groups)
        b = duration * i / len(groups)
        p = work / f"chunk_{i:02d}.wav"
        _export_slice(vocals, a, b, p)
        mapping.append({
            "chunk": i, "path": p.name, "start": a, "end": b,
            "lines": [{"time": a, "text": " ".join(g)}],
        })
    write_json(work / "chunk_mapping.json", mapping)
    return mapping
