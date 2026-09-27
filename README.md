# Phase 2 — Standalone Telugu Word-Level Lyric Synchronisation

Project version: **1.3.0**

This repository is a standalone batch-processing project. It does not integrate with, import, or modify the Phase 1 codebase.

## 1. Input contract

Put one complete package in `songs/original/` using the same basename:

```text
songs/original/
├── SongName.mp3
├── SongName.lrc
└── SongName.json
```

The MP3 is the audio source. The external LRC is the lyric/reference/timing source. The JSON is the cumulative historical/source metadata record.

The project does **not** require lyric frames embedded in the MP3. If embedded `USLT` or `SYLT` frames already exist, they are treated as existing MP3 metadata and are preserved.

## 2. Output contract

The only user-facing per-song output files are:

```text
songs/final/
├── SongName.mp3
├── SongName.lrc
└── SongName.json
```

The original files remain in `songs/original/` and are read-only.

## 3. Metadata preservation

### MP3

The final MP3 starts as a byte-for-byte copy of the input and is then updated with one Phase-2-owned `SYLT` frame:

```text
SYLT:Phase2-WordLevel:tel
```

Existing artwork, IDs, URLs, TXXX frames, USLT/SYLT frames, and other metadata are preserved. Phase 2 never wipes and rebuilds the ID3 tag set.

### JSON

The input JSON is deep-copied. All pre-existing fields are retained. New information is placed under the top-level `phase2` object. Only that namespace is owned by this project.

The JSON contains a canonical/self content hash under `phase2.outputs.final_json_sha256`. This is deliberately a content hash with that field excluded; the actual final JSON byte hash is stored in `phase2.db` because an exact byte hash embedded inside its own file is recursively self-referential.

## 4. Core alignment architecture

```text
MP3
 |
 +--> decode -> 16 kHz mono working audio
 |
 +--> Demucs -> vocals
 |
 `--> preserve existing MP3 metadata

LRC
 |
 +--> line text
 +--> coarse timestamps
 `--> blank timing markers / long gaps

JSON
 |
 `--> preserve complete historical record

vocals + LRC reference
 |
vocal activity analysis
 |
reversible Telugu normalization
 |
reference-aware overlapping chunks
 |
MMS Telugu acoustic emissions
 |
CTC reference forced alignment
 |
token spans
 |
token -> word spans
 |
canonical word timeline
 |
+--> final LRC
+--> final MP3 SYLT
`--> final JSON phase2 metadata
```

The central algorithm is **reference-driven CTC alignment**. MMS is used to produce frame-level acoustic evidence. The supplied LRC lyric text remains the reference transcript; the system does not substitute an ASR transcript for the user's lyric.

## 5. Environment

Recommended baseline:

- Python 3.11–3.13
- ffmpeg + ffprobe on PATH
- NVIDIA CUDA environment for practical large-batch processing, with CPU fallback

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For CUDA, install the PyTorch wheel/index that matches the host driver and intended CUDA runtime before running the pipeline when the generic pip resolver does not provide the desired CUDA build.

Run environment diagnostics:

```bash
python main.py --doctor
```

On Windows, `ffmpeg` and `ffprobe` must be available on `PATH`. Phase 2 writes decode scratch files with a `.wav` suffix and explicitly selects the WAV muxer so FFmpeg can identify the output format correctly.

## 6. First validation run

Check file pairing without processing:

```bash
python main.py --scan-only
```

Perform a database-only dry run:

```bash
python main.py --dry-run
```

Run the test suite:

```bash
python -m pytest
```

Compile all Python source:

```bash
python -m compileall -q main.py src tests
```

## 7. Processing commands

All songs:

```bash
python main.py --all
```

One song:

```bash
python main.py --song "001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra"
```

Several explicit songs:

```bash
python main.py --song "Song A" --song "Song B"
```

Retry quality classes:

```bash
python main.py --failed
python main.py --partial
python main.py --needs-review
```

Force a fresh Phase-2 computation:

```bash
python main.py --all --force
```

Keep temporary debug artifacts:

```bash
python main.py --all --keep-temp --debug
```

Recover stale in-progress database states:

```bash
python main.py --recover
```

Reconcile the database with already-promoted final packages:

```bash
python main.py --reconcile
# same operation, plan-compatible alias:
python main.py --repair-state
```

Back up the SQLite database:

```bash
python main.py --backup-db db/phase2_backup.sqlite
```

## 8. Model behavior

The MMS model is loaded once per process and configured for the Telugu adapter `tel`. The model cache lives under `models/mms/`.

The CTC aligner is implemented in `src/ctc_aligner.py`. It uses an expanded CTC topology with correct handling for repeated reference labels. It does not call deprecated high-level forced-alignment helpers.

## 9. Chunking

Chunks have:

- a logical lyric/reference interval;
- an audio interval supplied to the acoustic model;
- context padding around the logical interval;
- exact millisecond boundaries.

External LRC blank timestamp markers are treated as high-priority evidence for lyric-free gaps. VAD and energy activity are supporting signals, not proof by themselves that a section is instrumental.

## 10. Reversible Telugu normalization

Normalization is used only for alignment. The original lyric spelling remains available for final user-facing output.

Examples of reversible operations include:

- Unicode NFC normalization;
- whitespace normalization;
- optional number-to-Telugu conversion;
- configurable abbreviation expansion;
- punctuation/script filtering for the model reference.

Every word retains its original form and its normalized form.

## 11. Quality states

Pipeline state and quality state are deliberately independent.

Pipeline state tracks where processing is:

```text
pending -> scanning -> lyrics_loaded -> isolating -> isolated
-> chunking -> chunked -> aligning -> aligned -> merging -> merged
-> validating -> validated -> embedding -> finished
```

Quality state is one of:

```text
good
partial
needs_review
failed
```

## 12. Resume and idempotency

The database records input hashes, pipeline version, model revision, configuration hash, chunk status, chunk attempts, output hashes, and package ID.

Unchanged inputs with valid final outputs are skipped unless `--force` is used.

Successful chunks have persistent result JSON files and are not recomputed unnecessarily after a restart.

## 13. Final JSON content hash convention

`phase2.outputs.final_json_sha256` is a **canonical content hash excluding that field itself**.

The true byte hash of `songs/final/SongName.json` is stored in the database as `songs.final_json_sha256`.

This is intentional and prevents an impossible recursive requirement where a file contains the SHA-256 of its own final bytes.

## 14. Copyright / model licensing

The MMS model card lists `CC-BY-NC-4.0`. Review the applicable model and dependency licenses before any commercial deployment.

## 15. Large batch recommendations

For a large collection:

1. Validate the environment first.
2. Run the unit tests.
3. Run a small sample batch.
4. Inspect final MP3 metadata and word timings.
5. Run several complete songs with different structures.
6. Only then start the full batch.

The pipeline is intentionally restartable so a long batch can be stopped and resumed without discarding successful chunk results.

## 16. Important directories

```text
src/              source code
sql/              SQLite schema
tests/            automated tests
docs/             plan and audit documentation
songs/original/   read-only input
songs/final/      final user-facing output
temp/             per-song working data
models/mms/       cached MMS model files
db/               phase2.db and optional backups
```

## 17. What is not included

Model weights are not bundled in the project archive. They are downloaded into the configured model cache on first use when `models.allow_download` is enabled.

No user song audio or lyric corpus is bundled as a project fixture.

## 16. Recovery after an interrupted batch

A stopped batch does not invalidate the original files. Rerun:

```bash
python main.py --all
```

For songs that failed before a checkpoint artifact was created, the pipeline will retry the failed stage. Successful checkpoint artifacts are reused. Use `--force` only when you intentionally want to discard Phase-2 checkpoint data and recompute the song.

If you interrupted the process with Ctrl+C, the program exits cleanly with status 130 and leaves the current source MP3/LRC/JSON untouched.

## 17. Common Windows FFmpeg error

If an older build reports:

```text
Unable to choose an output format for ...source_16k.wav.tmp
``

the decoder is using an invalid temporary output filename for FFmpeg's format inference. The current implementation uses a `.wav` temporary filename plus `-f wav`. Update to the current `src/audio.py` before resuming the batch.


## Critical Windows/NVIDIA note

This release is CUDA-first. The default config requires CUDA and will refuse to silently fall back to CPU. The pinned production wheels are `torch==2.9.1+cu128` and `torchaudio==2.9.1+cu128`.

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cuda.ps1
python main.py --doctor
```

Then verify with `nvidia-smi -l 1` while processing.

## Recovery after the old SYLT chronology failures

The previous failure `MP3_VALIDATION_FAILED: SYLT timestamps are not chronological` was caused by a global alignment-order problem surfacing only at the final MP3 validation gate. This release: keeps the final SYLT validator strict, validates global chronology before output generation, repairs only small cross-chunk backward shifts, and logs the repair in the Phase 2 JSON. Never fix chronology by sorting timestamps, because sorting would detach timestamps from their words.

After replacing the project, normal `python main.py --all` can reuse persisted chunk results and retry/rebuild the final package. Do not use `--force` unless you intentionally want to discard checkpoints.


## 12. Field error recovery — SYLT chronology

The batch can encounter `MP3_VALIDATION_FAILED: SYLT timestamps are not chronological` when a locally valid chunk alignment creates a backward jump at a chunk boundary. Phase 2 never fixes this by sorting timestamps. Instead, the canonical merger performs bounded cross-chunk continuity repair and the pipeline can retry the offending chunk with a strict logical-window alignment. The final LRC and SYLT validators remain strict safety gates.

If a run reports this error for a set of songs, rerun the same command after updating the project; existing successful songs can be skipped by their validated source/output identity, while failed songs reuse their saved checkpoints when available.

## 13. CUDA-first policy

The production `config.json` requires CUDA by default. If PyTorch is CPU-only, the program stops before processing the batch and tells you to run `scripts/install_windows_cuda.ps1`. CPU fallback is available only when explicitly enabled with `--allow-cpu-fallback`.


## Field chronology fix (1.2.0)

Source-LRC blank timestamps are treated as structural lyric boundaries rather than ordinary word events. Words are prevented from spilling across those boundaries, affected chunks can be retried with a hard endpoint, and the final LRC validator checks canonical word spans separately from blank-marker structure.

## Field LRC output-timing fix (1.3.0)

The 1.3.0 release addresses the second-stage failure where songs that survived MP3/SYLT validation could still fail with `LRC_GENERATION_FAILED: timestamps are not globally chronological`. The root causes were: (1) small regressions could occur inside a single CTC chunk, (2) repeated calls to the merger mutated chunk-result objects, allowing repairs to compound, and (3) the merger's chunk-level forward translation was not aware of blank-marker boundaries.

1.3.0 makes merge operations non-mutating, repairs small timestamp regressions at the affected reference word, performs a final output-timing normalization pass that respects explicit blank regions, and treats a word ending after a blank marker as a quality condition rather than a serialization failure when its start remains on the lyric side of the marker. No timestamp sorting is used. Large or suspicious repairs are recorded in the word `reason` field and surfaced through quality review metadata.

After replacing the project, use `python main.py --failed --debug` to reprocess the songs that failed under earlier releases.
