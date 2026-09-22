from __future__ import annotations
import re
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np
import soundfile as sf

def _load_audio(path, sr=16000):
    import librosa
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32, copy=False)

def first_vocal_segment(path, threshold=0.5):
    y = _load_audio(path, 16000)
    try:
        from silero_vad import load_silero_vad, get_speech_timestamps
        import torch
        model = load_silero_vad()
        ts = get_speech_timestamps(
            torch.tensor(y), model, threshold=threshold, sampling_rate=16000
        )
        if not ts:
            return 0.0, min(len(y) / 16000, 10.0)
        return ts[0]["start"] / 16000, ts[0]["end"] / 16000
    except Exception:
        frame = max(1, int(.03 * 16000))
        hop = max(1, int(.01 * 16000))
        rms = []
        for i in range(0, max(1, len(y) - frame), hop):
            rms.append(np.sqrt(np.mean(y[i:i + frame] ** 2) + 1e-12))
        base = np.percentile(rms, 75) if rms else 0.01
        idx = next((i for i, x in enumerate(rms) if x > max(base * .25, 0.01)), 0)
        start = idx * hop / 16000
        return start, min(start + 5.0, len(y) / 16000)

def slice_first_phrase(audio, out, threshold=0.5):
    y = _load_audio(audio, 16000)
    start, end = first_vocal_segment(audio, threshold)
    a = max(0.0, start - 1.0)
    b = min(len(y) / 16000.0, end + 1.0)
    if b <= a:
        raise RuntimeError("VAD produced an empty validation segment")
    sf.write(str(out), y[int(a * 16000):int(b * 16000)], 16000, subtype="PCM_16")
    return a, b

def whisper_transcribe(path, model_name="openai/whisper-tiny", device="cuda"):
    from transformers import pipeline
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_name,
        device=0 if device == "cuda" else -1,
    )
    out = pipe(
        str(path),
        generate_kwargs={"language": "telugu", "task": "transcribe"},
    )
    return out["text"].strip()

def normalize(s):
    return re.sub(r"\s+", "", s).strip()

def validate(champion_text, audio, work, cfg):
    phrase = work / "first_vocal_phrase.wav"
    slice_first_phrase(audio, phrase, float(cfg.processing.get("vad_threshold", .5)))
    trans = whisper_transcribe(
        phrase,
        cfg.processing.get("whisper_model", "openai/whisper-tiny"),
        cfg.processing.get("device", "cuda"),
    )
    first = " ".join(champion_text.splitlines()[:4])
    ratio = SequenceMatcher(None, normalize(trans), normalize(first)).ratio()
    (work / "validation.txt").write_text(
        f"Whisper: {trans}\nReference: {first}\nSimilarity: {ratio:.4f}\n",
        encoding="utf-8",
    )
    return ratio
