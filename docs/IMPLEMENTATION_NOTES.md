# Implementation Notes

## 1. Source of truth hierarchy

The project uses this hierarchy:

```text
Original MP3
  = audio + preserved existing metadata

Original LRC
  = user-facing lyric reference + coarse timing anchors

Original JSON
  = complete historical/source metadata record

Canonical Phase-2 alignment
  = word start/end + score + source classification

Final LRC / SYLT / phase2 JSON
  = projections of the same canonical alignment
```

## 2. Existing embedded lyrics

Some source MP3s may already contain `USLT` or `SYLT`. They are not the Phase-2 lyric source. Phase 2 reads the external `.lrc` file. Existing embedded frames are preserved because they are part of the original MP3 metadata.

## 3. Final JSON self-hash

An actual byte-level SHA-256 of a file cannot be embedded into the exact same final file without defining a self-excluding convention. The implementation therefore stores a canonical content hash excluding `phase2.outputs.final_json_sha256`, while the database stores the actual byte hash.

## 4. LRC output

The final `.lrc` is a word-level project-specific export. It uses one timestamp before every original word on each lyric line. It is not claimed to be universally supported by all LRC players.

## 5. CTC scoring

The per-word score is a path-derived geometric mean of CTC token probabilities across the aligned token span. It is a quality heuristic, not a calibrated probability.

## 6. VAD

VAD is activity evidence and a chunk/gap boundary signal. It is not treated as a definitive instrumental classifier.

## 7. Resume

A song checkpoint is safe only when the corresponding persistent artifact exists and can be parsed. DB state without a valid result artifact is treated as resumable rather than trusted blindly.

## Windows FFmpeg output

FFmpeg temporary decode files must keep the `.wav` output extension. A name such as `source_16k.wav.tmp` is interpreted by FFmpeg as having an unknown output format on Windows. The decoder therefore uses a temporary name such as `.source_16k.tmp-<pid>.wav` and explicitly selects `-f wav`, then atomically replaces the destination.


## Windows batch recovery after the decode fix

An older build can leave songs in `failed` state with `AUDIO_DECODE_FAILED` when FFmpeg receives a temporary filename ending in `.wav.tmp`. The current decoder fixes the root cause by retaining `.wav` on the temporary output and explicitly using `-f wav`. After updating the project, rerun `python main.py --all` without `--force`; failed songs whose checkpoint artifacts are absent will retry from the failed stage, while valid completed packages are skipped.

`KeyboardInterrupt` is handled at the CLI boundary and exits with code 130 after the database run is finalized, without modifying source MP3/LRC/JSON files.


## 2026-09-27 chronology hardening

A batch run exposed repeated `MP3_VALIDATION_FAILED: SYLT timestamps are not chronological` errors. The root cause was that overlapping chunk audio could create a small backward start-time shift at chunk boundaries, while the merger did not enforce a global song-order invariant. The fix is intentionally not a timestamp sort. The merger now performs global-reference interpolation and can translate a whole affected chunk forward by a bounded amount (`alignment.max_global_repair_ms`) when the violation is cross-chunk and small. The validator separately checks the complete song word sequence before LRC/SYLT generation. The final SYLT validator remains strict as a last gate.

## 2026-09-27 NVIDIA hardening

The default runtime is now CUDA-required. The package pins the official CUDA 12.8 PyTorch wheels (`torch==2.9.1+cu128`, `torchaudio==2.9.1+cu128`) and includes a Windows PowerShell installer. Demucs attempts CUDA, retries CUDA with a smaller segment after a detected CUDA OOM, and only uses CPU if explicitly permitted. MMS follows the same CUDA-first policy.
