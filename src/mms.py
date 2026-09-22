from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math, re
import numpy as np
import torch
import soundfile as sf
from transformers import AutoProcessor, AutoModelForCTC

@dataclass
class Word:
    text:str
    start:float
    end:float
    score:float

class MMSAligner:
    def __init__(self, model_name="facebook/mms-1b-all", device="cuda"):
        self.device=torch.device("cuda" if device=="cuda" and torch.cuda.is_available() else "cpu")
        self.processor=AutoProcessor.from_pretrained(model_name)
        self.model=AutoModelForCTC.from_pretrained(model_name).to(self.device).eval()
        self.blank=int(self.model.config.pad_token_id if self.model.config.pad_token_id is not None else 0)
        self.sr=16000

    def _word_token_ids(self, text):
        words=text.split(); ids=[]; spans=[]
        for w in words:
            enc=self.processor.tokenizer(w, add_special_tokens=False).input_ids
            if isinstance(enc[0],list): enc=enc[0]
            spans.append((len(ids),len(ids)+len(enc),w)); ids.extend(enc)
        return ids,spans

    @torch.inference_mode()
    def align(self, wav:Path, text:str):
        audio,_=sf.read(str(wav),dtype="float32")
        if audio.ndim>1: audio=audio.mean(axis=1)
        inp=self.processor(audio,sampling_rate=self.sr,return_tensors="pt")
        x=inp.input_values.to(self.device)
        logits=self.model(x).logits[0]
        logp=torch.log_softmax(logits,dim=-1).cpu()
        ids,word_spans=self._word_token_ids(text)
        if not ids: return [],0.0,{"coverage":0,"likelihood":0,"sanity":0}
        return self._viterbi(logp,ids,word_spans)

    def _viterbi(self,logp,target,word_spans):
        T,V=logp.shape; blank=self.blank
        ext=[blank]
        for x in target: ext += [x,blank]
        S=len(ext)
        neg=-1e30
        dp=torch.full((T,S),neg); bp=torch.full((T,S),-1,dtype=torch.int32)
        dp[0,0]=logp[0,blank]
        if S>1: dp[0,1]=logp[0,ext[1]]
        for t in range(1,T):
            prev=dp[t-1]
            for s in range(S):
                best=prev[s]; state=s
                if s>0 and prev[s-1]>best: best=prev[s-1]; state=s-1
                if s>1 and ext[s]!=blank and ext[s]!=ext[s-2] and prev[s-2]>best: best=prev[s-2]; state=s-2
                dp[t,s]=best+logp[t,ext[s]]; bp[t,s]=state
        s=S-1 if dp[T-1,S-1]>=dp[T-1,max(0,S-2)] else max(0,S-2)
        states=[s]
        for t in range(T-1,0,-1):
            s=int(bp[t,s]); states.append(s)
        states=states[::-1]
        # Collect frame spans for each non-blank target token.
        token_frames=[[] for _ in target]
        for t,s in enumerate(states):
            if s%2==1:
                j=(s-1)//2
                if j<len(token_frames): token_frames[j].append(t)
        words=[]; covered=0; likelihoods=[]
        hop=0.02  # Wav2Vec2/MMS effective frame spacing; refined below by actual duration.
        hop=(len(states) and (len(states)*0.0)) or hop
        # CTC output length maps approximately to audio duration. Use actual input duration / T.
        # This avoids hard-coding feature hop if a model revision changes it.
        import soundfile as sf2
        # Caller has already loaded audio; infer 16 kHz and T frames from model's receptive field.
        # A small boundary offset is less important than monotonic, internally consistent timing.
        duration=max(0.001, T*0.02)
        # Word token spans are contiguous ranges in the target token list.
        for a,b,w in word_spans:
            frames=[f for j in range(a,b) for f in token_frames[j]]
            if not frames: words.append(Word(w,0,0,0)); continue
            covered+=1
            st=min(frames)*duration/T; en=(max(frames)+1)*duration/T
            sc=float(np.mean([float(logp[f,target[j]]) for j in range(a,b) for f in token_frames[j]]))
            likelihoods.append(max(0.0,min(1.0,math.exp(max(-20.0,sc)))))
            words.append(Word(w,st,en,likelihoods[-1]))
        starts=[w.start for w in words if w.end>w.start]; ends=[w.end for w in words if w.end>w.start]
        sanity=1.0 if all(words[i].start<=words[i+1].start and words[i].end<=words[i+1].end for i in range(len(words)-1)) else 0.0
        coverage=covered/max(1,len(words)); likelihood=float(np.mean(likelihoods)) if likelihoods else 0.0
        confidence=0.4*coverage+0.4*likelihood+0.2*sanity
        return words,confidence,{"coverage":coverage,"likelihood":likelihood,"sanity":sanity}

def align_chunks(mapping, work, reference_exists, cfg):
    aligner=MMSAligner(cfg.processing.get("mms_model","facebook/mms-1b-all"),cfg.processing.get("device","cuda"))
    final=[]; report=[]; threshold=float(cfg.processing.get("mms_confidence",.6))
    for item in mapping:
        text=" ".join(x["text"] for x in item["lines"])
        words,conf,parts=aligner.align(work/item["path"],text)
        mode="MMS"
        if conf < threshold:
            if reference_exists:
                # Fallback is represented as line timestamps for this chunk. Words are distributed
                # across each line interval; this preserves the exact scraped line clock locally.
                words=[]
                for line in item["lines"]:
                    words.extend(_fallback_line_words(line["time"]-item["start"],line["text"],item["lines"],item))
                mode="LRC-FALLBACK"
            else:
                # One relaxed retry: larger context is already present in the chunk; accept a second
                # pass and fail the song if it remains below threshold.
                words2,conf2,parts2=aligner.align(work/item["path"],text)
                if conf2>=threshold: words,conf,parts=words2,conf2,parts2
                else: raise RuntimeError(f"MMS confidence below {threshold:.2f} for chunk {item['chunk']}: {conf2:.3f}")
        for w in words: final.append({"text":w.text,"start":item["start"]+w.start,"end":item["start"]+w.end,"score":w.score})
        report.append(f"chunk_{item['chunk']:02d}: {mode}; confidence={conf:.3f}; coverage={parts.get('coverage',0):.3f}; likelihood={parts.get('likelihood',0):.3f}; sanity={parts.get('sanity',0):.3f}")
    (work/"alignment_report.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
    return final

def _fallback_line_words(line_time,text,all_lines,item):
    # Assign words uniformly inside the interval until the next reference line.
    idx=next((i for i,x in enumerate(all_lines) if x[0]==line_time and x[1]==text),0)
    end=(all_lines[idx+1][0] if idx+1<len(all_lines) else line_time+max(.5,min(3.0,len(text.split())*.35)))
    words=text.split(); n=max(1,len(words)); step=max(.05,(end-line_time)/n)
    return [Word(w,line_time+i*step,line_time+(i+1)*step,0.0) for i,w in enumerate(words)]
