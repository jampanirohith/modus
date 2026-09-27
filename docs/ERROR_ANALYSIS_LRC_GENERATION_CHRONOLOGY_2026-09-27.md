# Error Analysis — LRC Generation Chronology (2026-09-27)

## Observed field error

The batch reported repeated errors of the form:

`LRC_GENERATION_FAILED: lyric word timestamps are not globally chronological`

Example deltas observed in the field log included `29940 -> 28090`, `155170 -> 153350`, `214050 -> 213890`, `210690 -> 209830`, `250350 -> 248700`, and similar regressions.

The same run also reported blank-marker span messages such as a word ending after an explicit blank-marker timestamp.

## Root causes

1. The merger repaired only cross-chunk regressions. A timestamp regression inside a single chunk remained invalid.
2. `Merger.merge()` mutated the same `AlignedWord` objects stored inside `ChunkAlignment` results. The pipeline calls merge repeatedly during probing/retry/finalization, so one repair could affect later passes.
3. The old chunk-level forward translation did not constrain its shift by the lyric-safe region bounded by an explicit LRC blank marker. A repair could therefore fix global order while reintroducing a blank-region violation.
4. The LRC renderer treated a word end crossing a blank marker as a fatal serialization error even though LRC/SYLT output represents word onset timestamps; this made the output stage stricter than the actual rendered data required.

## 1.3.0 correction

- Merge candidates are copied before any repair so repeated merge calls are deterministic.
- Small regressions are repaired on the affected reference word, including same-chunk regressions.
- A final `finalize_output_timing()` pass constrains word starts/ends to the lyric region implied by explicit blank markers.
- Global timestamp order is normalized without sorting words.
- Blank-marker end-span crossing is no longer a serialization failure when the word start is still before the marker; the canonical end is clipped and the repair is recorded.
- A word beginning on the wrong side of a blank marker is still corrected/flagged.
- Final repair reasons are retained in the canonical word record and included in JSON.

## Recovery

Existing failed songs can be resumed with:

```powershell
python main.py --failed --debug
```

There is no need to delete the Hugging Face MMS cache or the Phase 2 database solely because of this error.
