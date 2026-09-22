from __future__ import annotations
import traceback, shutil
from pathlib import Path
from .db import connect, set_status, existing_isrc
from .spotify import SpotifyClient
from .downloader import download_spotify, download_youtube_audio
from .lyrics import collect, select_candidates, write_champion
from .validation import validate
from .demucs import separate
from .chunking import make_chunks, make_plain_chunks
from .mms import align_chunks
from .lrc import write_enhanced_lrc
from .youtube import prompt_url, cross_correlation_offset
from .master import create_master

class Pipeline:
    def __init__(self,cfg):
        self.cfg=cfg; self.playlist_db=cfg.path("db_dir")/"playlist.db"; self.songs_db=cfg.path("db_dir")/"songs.db"; self.temp=cfg.path("temp_dir"); self.songs=cfg.path("songs_dir")
        self.spotify=SpotifyClient(cfg)
    def ingest(self): return self.spotify.ingest(self.playlist_db)
    def pending(self):
        c=connect(self.playlist_db); rows=c.execute("SELECT * FROM playlist_entries WHERE status='pending' ORDER BY serial_number").fetchall(); c.close(); return rows
    def process(self, row, reset=False):
        serial=row["serial_number"]; work=self.temp/row["spotify_id"]; work.mkdir(parents=True,exist_ok=True)
        pc=connect(self.playlist_db)
        try:
            if reset: set_status(pc,serial,"pending",None)
            # Duplicate gate.
            if row["isrc"]:
                sc=connect(self.songs_db); dup=existing_isrc(sc,row["isrc"]); sc.close()
                if dup:
                    print(f"\nISRC duplicate found. Existing serial={dup['serial_number']} vs new serial={serial}")
                    choice=input("1=Keep Existing, 2=Replace Existing [default 1]: ").strip()
                    if choice!="2": set_status(pc,serial,"duplicate",None); shutil.rmtree(work,ignore_errors=True); return
                    oldwork=self.songs.parent/"temp"/str(dup["spotify_id"]); oldmp3=Path(dup["file_path"]) if dup["file_path"] else None; oldlrc=Path(dup["lrc_path"]) if dup["lrc_path"] else None
                    for p in (oldmp3,oldlrc):
                        if p: p.unlink(missing_ok=True)
                    sc=connect(self.songs_db); sc.execute("DELETE FROM songs WHERE serial_number=?",(dup["serial_number"],)); sc.commit(); sc.close()
                    pc.execute("UPDATE playlist_entries SET status='duplicate',updated_at=CURRENT_TIMESTAMP WHERE serial_number=?",(dup["serial_number"],)); pc.commit()
            meta=self.spotify.metadata(row["spotify_id"]); meta["serial"]=serial
            audio=download_spotify(meta["spotify_url"],work)
            candidates=collect(meta["title"],meta["artist"],self.cfg,work/"lyrics")
            ranked,champ=select_candidates(candidates)
            if not champ: raise RuntimeError("No lyric candidate survived the Telugu TCR >= 0.30 hard filter")
            # Validate champions in bucket order; dethrone only inside the same bucket before dropping tier.
            chosen=None; chosen_ref=None; chosen_clean=None
            for candidate in ranked:
                clean,ref=write_champion(candidate,work)
                try:
                    sim=validate(clean,audio,work,self.cfg)
                except Exception as e:
                    if candidate is ranked[-1]: raise
                    continue
                if sim>float(self.cfg.processing["validation_similarity"]): chosen=candidate; chosen_ref=ref; chosen_clean=clean; break
            if not chosen: raise RuntimeError("All eligible lyric candidates failed VAD/Whisper validation")
            vocals,_=separate(audio,work,self.cfg.processing["demucs_model"],self.cfg.processing["device"])
            if not chosen_ref:
                mapping=make_plain_chunks(vocals,chosen_clean,work,self.cfg); ref_exists=False
            else:
                mapping=make_chunks(vocals,chosen_ref,work,self.cfg); ref_exists=True
            words=align_chunks(mapping,work,ref_exists,self.cfg)
            lrc=write_enhanced_lrc(mapping,words,work/"aligned.lrc")
            yturl=prompt_url(meta["title"],meta["artist"],serial)
            yta=download_youtube_audio(yturl,work); offset=cross_correlation_offset(audio,yta)
            master,sidecar=create_master(audio,lrc,chosen_clean,meta,yturl,offset,self.songs)
            sc=connect(self.songs_db)
            sc.execute("""INSERT OR REPLACE INTO songs(serial_number,spotify_id,title,artist,album,album_artist,release_date,duration,spotify_url,isrc,artwork_url,youtube_url,youtube_offset_seconds,file_path,lrc_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (serial,meta["spotify_id"],meta["title"],meta["artist"],meta.get("album"),meta.get("album_artist"),meta.get("release_date"),meta.get("duration"),meta.get("spotify_url"),meta.get("isrc"),meta.get("artwork_url"),yturl,offset,str(master),str(sidecar)))
            sc.commit(); sc.close(); set_status(pc,serial,"finished",None); shutil.rmtree(work,ignore_errors=True)
        except Exception as e:
            err=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=8)}"
            set_status(pc,serial,"error",err); print(f"\n[ERROR] serial {serial}: {e}")
        finally: pc.close()
