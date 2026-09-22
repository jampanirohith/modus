from __future__ import annotations
from dataclasses import dataclass, field
import re, unicodedata
from pathlib import Path

@dataclass
class Candidate:
    provider: str
    text: str
    kind: str = "plain"  # enhanced, line, plain
    tcr: float = 0.0
    score: float = 0.0
    path: Path|None = None
    notes: list[str] = field(default_factory=list)

TELUGU_RANGES=((0x0C00,0x0C7F),(0x1CDA,0x1CDF))
TAG_RE=re.compile(r"\[[^\]]*\]")
WORD_TS_RE=re.compile(r"<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>")
LINE_TS_RE=re.compile(r"^\s*\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\]")

def is_telugu(ch):
    return any(a<=ord(ch)<=b for a,b in TELUGU_RANGES)

def tcr(text):
    alpha=[c for c in text if unicodedata.category(c).startswith("L")]
    return sum(is_telugu(c) for c in alpha)/len(alpha) if alpha else 0.0

def detect_kind(text):
    lines=[x for x in text.splitlines() if x.strip()]
    if any(WORD_TS_RE.search(x) for x in lines): return "enhanced"
    if any(LINE_TS_RE.match(x) for x in lines): return "line"
    return "plain"

def strip_word_tags(s): return WORD_TS_RE.sub("",s)
def strip_line_ts(s): return LINE_TS_RE.sub("",s)
def clean_plain(text):
    out=[]
    for line in text.splitlines():
        line=strip_word_tags(strip_line_ts(line))
        line=re.sub(r"\[[^\]]*\]", "", line).strip()
        if line: out.append(line)
    return "\n".join(out)

def parse_sync(text):
    """Return [(time, clean_line, original_line)] for standard/enhanced LRC."""
    result=[]
    for raw in text.splitlines():
        times=re.findall(r"\[(\d{1,3}:\d{2}(?:[.:]\d{1,3})?)\]",raw)
        if not times: continue
        body=re.sub(r"\[[^\]]*\]", "", raw)
        body=WORD_TS_RE.sub("",body).strip()
        if not body: continue
        for ts in times:
            mm,ss=ts.split(":",1); sec=int(mm)*60+float(ss.replace(":","."))
            result.append((sec,body,raw))
    return sorted(result,key=lambda x:x[0])

def enhanced_word_tokens(text):
    """Parse an enhanced LRC line into [(absolute_time, word)]."""
    m=re.match(r"\[(\d{1,3}:\d{2}(?:[.:]\d{1,3})?)\](.*)$",text.strip())
    if not m: return []
    base=float(m.group(1).split(":")[0])*60+float(m.group(1).split(":")[1].replace(":","."))
    body=m.group(2)
    toks=[]
    for tm,word in re.findall(r"<(\d{1,3}:\d{2}(?:[.:]\d{1,3})?)>\s*([^<]+?)(?=\s*<|$)",body):
        a,b=tm.split(":",1); toks.append((int(a)*60+float(b.replace(":",".")),word.strip()))
    return toks

def collect(title, artist, cfg, work):
    candidates=[]; q=f"{title} {artist}"
    # Layer 1
    try:
        import syncedlyrics
        for enhanced in (True,False):
            value=syncedlyrics.search(q, enhanced=enhanced)
            if value:
                kind="enhanced" if enhanced and WORD_TS_RE.search(value) else detect_kind(value)
                candidates.append(Candidate("syncedlyrics",value,kind))
                if kind=="enhanced": break
    except Exception as e: candidates.append(Candidate("syncedlyrics","","plain",notes=[f"provider error: {e}"]))
    # Layer 2
    try:
        from ytmusicapi import YTMusic
        yt=YTMusic()
        results=yt.search(q,filter="songs",limit=5)
        for r in results:
            vid=r.get("videoId")
            if not vid: continue
            try:
                song=yt.get_song(vid)
                lyr=song.get("lyrics") if isinstance(song,dict) else None
                browse=(lyr or {}).get("browseId") if isinstance(lyr,dict) else None
                if browse:
                    data=yt.get_lyrics(browse)
                    text=data.get("lyrics") if isinstance(data,dict) else None
                    if text: candidates.append(Candidate("ytmusicapi",text,detect_kind(text)))
            except Exception: continue
            if len(candidates)>6: break
    except Exception as e: candidates.append(Candidate("ytmusicapi","","plain",notes=[f"provider error: {e}"]))
    # Layer 3
    token=cfg.genius.get("access_token")
    if token:
        try:
            import lyricsgenius
            g=lyricsgenius.Genius(token, timeout=15, retries=1, remove_section_headers=False)
            song=g.search_song(title,artist)
            if song and song.lyrics: candidates.append(Candidate("lyricsgenius",song.lyrics, "plain"))
        except Exception as e: candidates.append(Candidate("lyricsgenius","","plain",notes=[f"provider error: {e}"]))
    work.mkdir(parents=True,exist_ok=True)
    for i,c in enumerate(candidates,1):
        if c.text:
            c.tcr=tcr(c.text); c.path=work/f"candidate_{i:02d}_{c.provider}.txt"; c.path.write_text(c.text,encoding="utf-8")
    return [c for c in candidates if c.text]

def rank_completeness(c):
    text=clean_plain(c.text); words=re.findall(r"\S+",text); tel=sum(is_telugu(x) for x in text)
    # Length is used only within a tier, matching the spec's "most complete" rule.
    return (len(words), len(text), tel)

def select_candidates(candidates):
    eligible=[c for c in candidates if c.tcr>=0.30]
    buckets={"enhanced":[],"line":[],"plain":[]}
    for c in eligible: buckets[c.kind if c.kind in buckets else "plain"].append(c)
    for kind in ("enhanced","line","plain"):
        if buckets[kind]:
            buckets[kind].sort(key=rank_completeness,reverse=True)
            return buckets[kind], buckets[kind][0]
    return [],None

def write_champion(champion, work):
    clean=clean_plain(champion.text)
    (work/"best_telugu_lyrics.txt").write_text(clean,encoding="utf-8")
    ref=None
    if champion.kind in ("enhanced","line"):
        ref=work/"reference_sync.lrc"; ref.write_text(champion.text,encoding="utf-8")
    return clean,ref
