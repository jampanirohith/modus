# Canonical Song + Telugu Enhanced LRC — Phase 1

Production implementation of the supplied Phase 1 specification. The system ingests a Spotify playlist, assigns immutable serials, detects ISRC duplicates, downloads one master audio reference, gathers Telugu lyric candidates, validates the champion acoustically, separates vocals, creates collision-safe semantic chunks, performs MMS word alignment with per-chunk fallback, captures a manually curated YouTube URL, measures the YouTube audio offset, writes a metadata-rich canonical MP3, commits both SQLite databases, and cleans temporary work.

## Pipeline

`Spotify playlist -> playlist.db -> ISRC gate -> spotdl master -> lyrics candidates -> Telugu TCR filter -> tier selection -> VAD + Whisper validation -> Demucs -> semantic chunks -> MMS / LRC fallback -> Enhanced LRC -> manual YouTube URL -> yt-dlp -> cross-correlation -> canonical MP3 + sidecar LRC -> DB commit -> cleanup`

## Requirements

- Python 3.11+ recommended.
- FFmpeg available on PATH.
- NVIDIA GPU + CUDA-enabled PyTorch for Demucs and MMS.
- Spotify Developer application credentials.
- Genius token for the final plain-text fallback.
- A Spotify account suitable for the requested SpotDL workflow.

Install:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and fill credentials. Do not commit `config.json`.

## Run

```powershell
python main.py
python process_single.py 12
```

`main.py` only processes `pending` rows. `error`, `finished`, and `duplicate` are ignored. `process_single.py` resets one selected error row to `pending` and reruns Steps 2–13.

## Important implementation notes

- Spotify audio is always the timing master.
- Missing ISRC means duplicate detection is skipped.
- TCR is calculated over alphabetic characters; candidates below 0.30 are rejected.
- Tier order is Word-Enhanced LRC > line LRC > plain text.
- Plain text candidates do not create `reference_sync.lrc`.
- Whisper validation uses the first VAD vocal region plus a one-second context buffer.
- Demucs runs on the complete master track, never pre-chunked audio.
- Chunk buffers are clamped to actual adjacent gaps so overlap cannot occur.
- MMS confidence combines word coverage, normalized alignment likelihood, and timestamp sanity.
- If a synced source exists, a low-confidence chunk falls back only for that chunk; plain-text-only songs retry MMS once and otherwise fail.
- The YouTube URL is deliberately manual and is not auto-searched or validated.
- Database commit occurs only after the entire pipeline succeeds.

## Spotify API compatibility fix

The playlist ingestion layer is compatible with the current Spotify playlist-items response shape, where the actual track object is under `entry["item"]`. It also accepts the older `entry["track"]` shape as a fallback. The ingestion code paginates the complete playlist, preserves exact entry order, skips unavailable/non-track entries safely, and reports sync counts.

If you previously ran the project while ingestion was broken, rerun `python main.py`. Existing successfully inserted Spotify IDs are ignored exactly as required by the Phase 1 append-only rule; no database deletion is required.
