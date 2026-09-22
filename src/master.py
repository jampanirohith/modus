from __future__ import annotations
from pathlib import Path
import requests, shutil
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TPE2, TDRC, TSRC, APIC, USLT, SYLT, TXXX
from mutagen.mp3 import MP3
from .utils import safe_filename

def _id3(path):
    try: tags=ID3(path)
    except ID3NoHeaderError: tags=ID3()
    return tags

def create_master(audio, lrc, clean_text, metadata, youtube_url, offset, songs_dir):
    name=f"{metadata['serial']:03d}_{safe_filename(metadata['title']).replace(' ','_')}.mp3"
    out=songs_dir/name; shutil.copy2(audio,out)
    tags=_id3(out)
    def add(frame): tags.delall(frame.FrameID); tags.add(frame)
    add(TIT2(encoding=3,text=metadata["title"]))
    add(TPE1(encoding=3,text=metadata["artist"]))
    if metadata.get("album"): add(TALB(encoding=3,text=metadata["album"]))
    if metadata.get("album_artist"): add(TPE2(encoding=3,text=metadata["album_artist"]))
    if metadata.get("release_date"): add(TDRC(encoding=3,text=metadata["release_date"]))
    if metadata.get("isrc"): add(TSRC(encoding=3,text=metadata["isrc"]))
    fields={"SPOTIFY_TRACK_ID":metadata["spotify_id"],"SPOTIFY_URL":metadata.get("spotify_url",""),"YOUTUBE_URL":youtube_url,
            "YOUTUBE_OFFSET_SECONDS":f"{offset:.3f}","LRC_FORMAT":"ENHANCED_WORD_SYNCED"}
    for k,v in fields.items(): tags.delall(f"TXXX:{k}"); tags.add(TXXX(encoding=3,desc=k,text=[str(v)]))
    tags.delall("USLT:eng:"); tags.add(USLT(encoding=3,lang="eng",desc="",text=clean_text))
    # SYLT entries are populated from the enhanced LRC sidecar.
    import re
    entries=[]
    for line in lrc.read_text(encoding="utf-8").splitlines():
        for tm,w in re.findall(r"<(\d{2}:\d{2}\.\d{2})>([^<]+)",line):
            mm,ss=tm.split(":"); ms=int((int(mm)*60+float(ss))*1000); entries.append((w.strip(),ms))
    tags.delall("SYLT:eng:"); tags.add(SYLT(encoding=3,lang="eng",format=2,desc="",text=entries))
    if metadata.get("artwork_url"):
        try:
            data=requests.get(metadata["artwork_url"],timeout=20).content
            tags.delall("APIC:"); tags.add(APIC(encoding=3,mime="image/jpeg",type=3,desc="Cover",data=data))
        except Exception: pass
    tags.save(out,v2_version=4)
    verify=ID3(out)
    required=["TXXX:SPOTIFY_TRACK_ID","TXXX:SPOTIFY_URL","TXXX:YOUTUBE_URL","TXXX:YOUTUBE_OFFSET_SECONDS","TXXX:LRC_FORMAT","SYLT:eng:"]
    missing=[x for x in required if x not in verify]
    if missing: raise RuntimeError(f"ID3 verification failed; missing {missing}")
    sidecar=songs_dir/(out.stem+".lrc"); shutil.copy2(lrc,sidecar)
    return out,sidecar
