from __future__ import annotations
from pathlib import Path
import numpy as np
import librosa

def prompt_url(title,artist,serial):
    print(f"\nYouTube curation required\nSerial: {serial}\nSong: {title} — {artist}")
    return input("Paste the official YouTube video song URL: ").strip()

def cross_correlation_offset(spotify_audio:Path,youtube_audio:Path):
    # Downsampled mono correlation is much faster and sufficiently precise for video mux offset.
    sr=8000
    ref,_=librosa.load(str(spotify_audio),sr=sr,mono=True)
    yt,_=librosa.load(str(youtube_audio),sr=sr,mono=True)
    if len(ref)>sr*60: ref=ref[:sr*60]
    if len(yt)>sr*300: yt=yt[:sr*300]
    ref=ref/(np.std(ref)+1e-9); yt=yt/(np.std(yt)+1e-9)
    # Use FFT convolution to find lag of reference inside YouTube audio.
    corr=librosa.util.fftconvolve(yt,ref[::-1],mode="full")
    lags=np.arange(-len(ref)+1,len(yt))
    idx=int(np.argmax(corr)); lag=int(lags[idx])
    return lag/sr
