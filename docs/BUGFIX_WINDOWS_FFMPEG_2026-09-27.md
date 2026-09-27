# Windows FFmpeg Decode Bug Fix — 2026-09-27

## Observed failure

The batch stopped every song at the audio decoding stage with:

```text
Unable to choose an output format for ...\source_16k.wav.tmp
```

The common filename pattern was the cause: FFmpeg sees `.tmp` as the final extension and cannot infer the WAV muxer.

## Fix

`src/audio.py` now:

1. Creates a temporary file with a `.wav` suffix, for example `.source_16k.tmp-1234.wav`.
2. Explicitly passes `-f wav`.
3. Writes `pcm_f32le`.
4. Atomically replaces the requested destination.
5. Removes the temporary file after success or failure.

## Recovery

Do not rebuild all Phase-2 checkpoints merely because the previous run failed at decoding. Run:

```text
python main.py --all
```

The previously failed songs can retry from the missing decode artifact. Use `--force` only for an intentional clean recomputation.

## Secondary log event

The final `KeyboardInterrupt` in the supplied log occurred while the program was reading the next JSON after 53 repeated decode failures. It was an interruption of the batch process, not evidence of a second decoding defect. The CLI now handles Ctrl+C cleanly.
