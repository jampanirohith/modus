# Implementation audit

This repository implements the supplied `final.txt` Phase 1 specification as executable Python modules. The architecture remains two SQLite databases, append-only serial assignment, strict lyric tiers, VAD/Whisper validation, full-track Demucs, dynamic chunking, MMS per-chunk alignment, manual YouTube curation, cross-correlation, ID3v2.4 canonicalization, transactional final commit, and isolated batch errors.

## Intentional engineering details

1. Provider failures are captured while allowing the other lyric layers to run.
2. Plain-text Tier C never creates an authoritative `reference_sync.lrc`; it uses an internal chunk mapping so MMS remains possible, but it has no line-timestamp fallback.
3. The MMS aligner uses CTC Viterbi decoding over the exact lyric token sequence, then converts token spans to word timestamps.
4. Low-confidence synced chunks use local line-level fallback; plain-text chunks get exactly one relaxed MMS retry before failing.
5. YouTube offset correlation is computed against normalized mono audio at 8 kHz for practical runtime.
6. ID3 tags are read back and verified before DB commit.
