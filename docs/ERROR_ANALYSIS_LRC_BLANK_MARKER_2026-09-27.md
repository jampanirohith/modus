# Field Error Analysis — LRC_GENERATION_FAILED: timestamps are not globally chronological

## Observed behavior

A follow-up field run reduced the terminal error from SYLT validation to LRC generation. The affected songs reported:

```text
LRC_GENERATION_FAILED: timestamps are not globally chronological
```

## Root cause

The final LRC renderer included source-LRC blank-marker timestamps in the same generic chronological stream as word timestamps. More importantly, model audio had post-boundary context, so a word from the final lyric line before an explicit blank/instrumental marker could be aligned after the marker.

A generic timestamp sort is not a valid repair because it would detach timing from lyric words.

## Correct behavior

1. Word timestamps are validated globally in reference order.
2. Explicit blank markers are treated as structural hard boundaries.
3. A lyric word before a marker must end at or before the marker.
4. The first lyric word after a marker must start at or after the marker.
5. A boundary violation triggers targeted chunk re-alignment with the marker as a hard audio endpoint.
6. Normal retry budgets are augmented by the dedicated global-repair retry budget, so a later process run can repair chunks that already consumed their ordinary attempts before the final-output validation failed.
7. LRC validation uses canonical word spans for boundary checks; it does not infer word end times from LRC text.

## Recovery

Existing songs whose chunks are already aligned do not need to redo all earlier work. Re-running `python main.py --all` loads saved chunk results, detects blank-boundary violations, and targets the affected chunks for repair.
