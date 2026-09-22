from __future__ import annotations
from pathlib import Path
from .utils import run

def separate(audio: Path, work: Path, model="htdemucs", device="cuda"):
    outroot=work/"demucs_out"; outroot.mkdir(exist_ok=True)
    cmd=[sys.executable,"-m","demucs","--name",model,"--out",str(outroot)]
    if device=="cuda": cmd += ["-d","cuda"]
    else: cmd += ["-d","cpu"]
    cmd += [str(audio)]
    run(cmd)
    stem=outroot/model/audio.stem
    vocals=stem/"vocals.wav"; accomp=stem/"no_vocals.wav"
    if not vocals.exists(): raise RuntimeError(f"Demucs vocals output missing: {vocals}")
    vocals.rename(work/"vocals.wav")
    if accomp.exists(): accomp.rename(work/"accompaniment.wav")
    return work/"vocals.wav", work/"accompaniment.wav"
