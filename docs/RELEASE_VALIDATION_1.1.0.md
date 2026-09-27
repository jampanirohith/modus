# Phase 2 Release Validation — 1.1.0

## Scope

This release is the standalone Phase 2 Telugu word-level lyric synchronization project.

Input contract:

```text
songs/original/<basename>.mp3
songs/original/<basename>.lrc
songs/original/<basename>.json
```

Output contract:

```text
songs/final/<basename>.mp3
songs/final/<basename>.lrc
songs/final/<basename>.json
```

## Field failures addressed

### Windows FFmpeg decode failure

The field run previously failed every song at audio decoding because a temporary WAV file was named with `.wav.tmp`, preventing FFmpeg from inferring the WAV muxer. The decoder now keeps `.wav` as the final suffix and explicitly passes `-f wav`.

### NVIDIA / CPU-only PyTorch

The field machine exposed an NVIDIA RTX 5050 through `nvidia-smi`, but PyTorch reported `Torch not compiled with CUDA enabled`. This release pins the Windows-compatible CUDA 12.8 PyTorch wheels, adds an installation script, verifies CUDA in `--doctor`, and requires CUDA by default. CPU fallback is opt-in only.

### SYLT chronological failure

The field batch had 48 songs fail with:

```text
MP3_VALIDATION_FAILED: SYLT timestamps are not chronological
```

The failure was traced to globally non-chronological canonical word timing across independently aligned chunks. This release does not sort timestamps. It repairs bounded cross-chunk backshifts by shifting the affected chunk while preserving word identity and duration, validates the merged timeline before output generation, and retries targeted chunks with a strict logical-window alignment when needed.

## Verification performed

- `python -m pytest -q` — 32 tests passed.
- `python -m compileall -q main.py src tests` — pass.
- `python main.py --help` — pass.
- `python main.py --dry-run` — pass.
- `python main.py --doctor` — pass in the build host; the build host has CPU-only PyTorch, so doctor correctly reports CUDA unavailable.
- Real supplied sample MP3/LRC/JSON package — scanner, LRC parser, FFmpeg decode, SQLite inventory, JSON preservation/self-hash, and metadata-preserving Phase-2 SYLT embedding smoke tests passed.

## Full ML limitation

A full Demucs + MMS + CTC end-to-end run was not executed on the build host because it has no CUDA device and does not contain the full production ML runtime. The project includes the production CUDA-first path and the complete alignment implementation, but the first full-song acceptance run must be performed on the user's NVIDIA machine after installing the pinned CUDA environment.

## Release invariants

- `songs/original/` is read-only.
- Existing MP3 metadata is preserved.
- Existing JSON content outside the `phase2` namespace is preserved.
- Final LRC and SYLT are generated from the same canonical word timeline.
- Original files are never overwritten.
- Final files are promoted only after validation.
- Existing successful songs can be reused; failed songs can resume from checkpoints.
