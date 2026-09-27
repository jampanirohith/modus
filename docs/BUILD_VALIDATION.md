# Build and Verification Report

## Automated build

- Python compilation: PASS
- Pytest suite: PASS — **32 tests passed**
- CLI help: PASS
- Doctor command: PASS (reports installed environment; missing optional ML packages/CUDA are reported rather than hidden)

## Real sample smoke checks

The supplied real MP3/LRC/JSON package was used for non-ML smoke checks:

- LRC parsing: PASS
- 39 lyric lines: PASS
- 3 blank timing markers: PASS
- Blank intervals derived from the LRC: PASS
- JSON preservation/self-hash contract: PASS
- Cross-file JSON-to-final-MP3/LRC consistency checks are implemented in the finalization stage.
- SQLite source inventory: PASS
- Real sample MP3 copied and Phase-2 SYLT added in a temporary location: PASS
- Existing MP3 metadata preservation validation: PASS
- Real FFmpeg decode smoke test: PASS — 16 kHz mono WAV produced successfully
- Windows FFmpeg `.wav.tmp` regression test: PASS

## ML execution limitation

The build host has no CUDA device and does not have the full Transformers/Silero runtime installed. Therefore the expensive Demucs + MMS + CTC end-to-end alignment was not executed here. The packaged project includes the runtime implementation, the dedicated CTC aligner, and tests/smoke checks, but a production deployment must perform the documented full-sample gate after installing the pinned environment.


## Batch-log fixes applied after field run

- Fixed the Windows FFmpeg temporary filename extension issue.
- Fixed global SYLT chronology failures by validating and repairing the canonical word timeline before output generation.
- Added field-error analysis and targeted cross-chunk strict-window retry behavior.
- Added global LRC timestamp validation.
- Added strict, explicit CUDA requirement by default.
- Added official CUDA 12.8 wheel installation/verification scripts.
- Routed the Hugging Face Hub cache to the project-owned `models/mms` location to avoid future duplicate checkpoint caching.
- Added Demucs CUDA OOM retry with a bounded segment size.
- Added clearer CUDA/model-device reporting to `--doctor` and model startup.
