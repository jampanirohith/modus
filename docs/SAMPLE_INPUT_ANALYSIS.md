# Real Sample Package Analysis

## Input files

```text
001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.mp3
001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.lrc
001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.json
```

## Observed structure

- Parsed LRC timestamp/blank entries: **42**
- Lyric lines: **39**
- Blank timing markers: **3**
- Candidate blank intervals at a 1.5 s minimum: **[(97290, 132940), (191720, 252820), (311910, 317592)]**
- MP3 duration observed by Mutagen: **317.592 s**
- JSON-declared song duration: **318 s**

## Architectural implications

1. The external sidecar LRC is a complete lyric/timing reference.
2. The blank LRC markers are valuable boundary evidence and should not become empty alignment targets.
3. The final lyric timestamp can be earlier than the audio end; the project must allow valid outros and intros.
4. The JSON is a cumulative source record and must be copied/updated without losing unknown fields.
5. The MP3 contains existing ID3 metadata and synchronized/unsynchronized lyric frames; Phase 2 treats those as protected metadata rather than its lyric source.

## Final output expectation

```text
songs/final/
├── 001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.mp3
├── 001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.lrc
└── 001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.json
```
