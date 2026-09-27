# Field Error Analysis — SYLT timestamps not chronological — 2026-09-27

## Observed field result

The 121-song batch completed with:

```text
finished = 71
skipped  = 2
failed   = 48
```

All 48 failures reported the same terminal error:

```text
MP3_VALIDATION_FAILED: SYLT timestamps are not chronological
```

This means the common failure is concentrated at final synchronized-lyrics validation, rather than 48 unrelated media/decode failures.

## Root cause

The previous implementation allowed locally valid chunk alignments to form a globally non-chronological reference timeline. Chunk audio has context overlap, so the first word of a later chunk can be placed slightly before the last word of the prior chunk. In addition, missing-word interpolation must be performed in global reference order rather than independently within a single lyric line.

Sorting timestamps after the fact is **not** a valid fix because it would detach timestamps from the words they were aligned to.

## Corrected flow

```text
CTC chunk alignment
        |
        v
chunk validation
        |
        v
global merge
        |
        v
small cross-chunk continuity repair
        |
        v
global chronology validation
        |
        +--> valid -> render LRC/SYLT
        |
        `--> invalid -> targeted strict-window chunk retry
```

## Repair policy

A small cross-chunk backward shift can be repaired by translating the entire affected chunk forward by the minimum required delta. The word durations and internal order remain unchanged.

Large shifts, same-chunk reversals, invalid spans, and unresolved global violations remain validation failures and can trigger targeted chunk re-alignment instead of being silently modified.

## Additional protection

The final project now validates chronology at three layers:

1. canonical merged word timeline;
2. rendered LRC timestamps;
3. final embedded SYLT timestamps.

The final SYLT validator also reports the exact violating index and the previous/current timestamp pair.

## Recovery

Existing finished songs can remain untouched. Failed songs retain their checkpoints/temp artifacts and are reprocessed from the last available safe stage when `python main.py --all` is rerun.

## Related implementation

- `src/merger.py` — global chronology detection and bounded continuity repair
- `src/pipeline.py` — targeted strict-window retries
- `src/validator.py` — canonical global chronology validation
- `src/lrc_generator.py` — rendered-LRC chronology validation
- `src/embedder.py` — final SYLT chronology validation
