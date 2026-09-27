# Phase 2 Release Validation — 1.2.0

## Field regression addressed

The follow-up field run moved the terminal error from final SYLT validation to:

```text
LRC_GENERATION_FAILED: timestamps are not globally chronological
```

The affected songs share a common structural condition: their source LRCs contain explicit blank/instrumental timing markers. The prior renderer mixed those structural markers with word-event timestamps, while the alignment audio still contained post-marker context. This permitted a previous lyric line's final word span to spill past the source LRC blank boundary.

## 1.2.0 behavior

- Blank markers are structural hard lyric boundaries.
- A lyric word before a marker must finish at or before the marker.
- The first lyric word after a marker must start at or after the marker.
- Targeted global-repair retries can re-align the affected chunk with the marker as a hard audio endpoint.
- Global repair has a separate attempt budget so a later run can repair chunks that already consumed ordinary attempts before final-output validation failed.
- WordBuilder no longer creates an invalid 1 ms span outside a strict endpoint.
- Missing-word interpolation respects explicit blank-marker boundaries.
- LRC chronological validation excludes structural blank markers from the ordinary word-event sequence and validates their position against the canonical word spans.
- Final MP3/SYLT validation remains a second-line defense.

## Recovery behavior

Existing finished outputs remain reusable. A subsequent:

```powershell
python main.py --all
```

will skip valid finished packages and retry the failed packages using their saved checkpoints. No source MP3/LRC/JSON file is modified.

## NVIDIA behavior

The production configuration remains CUDA-first:

```text
runtime.device = cuda
runtime.require_cuda = true
runtime.allow_cpu_fallback = false
```

The Windows installation script installs the pinned CUDA 12.8 PyTorch wheels and the verification script checks both PyTorch CUDA support and the NVIDIA driver/GPU.

## Verification

- Full automated Python suite: all tests passing in the build environment.
- Python compilation: pass.
- CLI help: pass.
- Real sample MP3/LRC/JSON scanner/decode/metadata smoke tests: pass.
- Explicit blank-marker boundary regression tests: pass.
- CTC alignment unit tests, repeated-label tests, merge/ordering tests: pass.
- Archive integrity: pass.
