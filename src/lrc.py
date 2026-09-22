from __future__ import annotations
from pathlib import Path
from .utils import format_ts

def write_enhanced_lrc(mapping, words, out: Path):
    pos=0; lines=[]
    for chunk in mapping:
        for line in chunk["lines"]:
            expected=line["text"].split(); selected=words[pos:pos+len(expected)]; pos+=len(expected)
            if not selected: continue
            base=selected[0]["start"]
            body=" ".join(f"<{format_ts(w['start'])}>{w['text']}" for w in selected)
            lines.append(f"[{format_ts(base)}]{body}")
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return out
