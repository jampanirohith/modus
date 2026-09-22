# Ultra-detailed implementation analysis

## 1. Architecture preserved

The supplied specification defines two independent SQLite databases. `playlist.db` owns immutable playlist serials and lifecycle state; `songs.db` owns canonical finished artifacts. The implementation keeps this separation and uses the playlist serial as the canonical identity.

## 2. Ingestion

`src/spotify.py` authenticates through Spotipy OAuth, paginates the complete playlist, preserves playlist entry order, ignores already-known Spotify IDs, and assigns `MAX(serial_number)+1` for new entries. The insert is append-only and starts at `pending`.

## 3. Duplicate control

An existing ISRC is checked only when the incoming ISRC is non-empty. A missing ISRC bypasses the duplicate gate exactly as specified. When a duplicate is found, the user can retain the existing master or replace it; the replacement path removes the previous canonical files and database row before processing the new serial.

## 4. Master audio

SpotDL is the only Spotify-audio acquisition step. The resulting `spotify_audio.mp3` becomes the timing master. Three attempts are made before the row becomes `error`.

## 5. Lyrics

The implementation queries `syncedlyrics`, YouTube Music, and Genius. Candidates retain provider and sync-type information. TCR is calculated using Unicode alphabetic characters, and candidates below 0.30 are removed before tier selection. Within a tier, completeness is approximated by token count, text length, and Telugu-character count. Tier order is absolute: enhanced, line-synced, then plain.

## 6. Champion split

The selected candidate is converted into `best_telugu_lyrics.txt`. Only enhanced or line-synced champions create the authoritative `reference_sync.lrc`. Plain-text Tier C intentionally does not create that file.

## 7. Acoustic validation

Silero VAD isolates the first speech region and adds one second of context. Whisper-tiny transcribes only that phrase. SequenceMatcher compares the transcript with the opening lyric stanza. Candidates are tried in descending quality order; validation must exceed the configured 0.80 threshold.

## 8. Demucs

Demucs receives the complete master track. No pre-Demucs chunking occurs. The expected `vocals.wav` is moved into the working directory.

## 9. Semantic chunking

Synced lyrics are grouped at pauses over 1.5 seconds, limited to 20 seconds, and merged when too small. Buffer sizes follow the supplied 0.3/1.0/2.0-second policy and are clamped against available gaps. Tier C has no timing map, so it uses a non-authoritative proportional text partition solely to feed MMS; it cannot use the scraped-LRC fallback.

## 10. MMS

`src/mms.py` loads `facebook/mms-1b-all`, tokenizes the exact Telugu text, and uses CTC Viterbi decoding to find the most probable path through the target token sequence. Word timestamps are recovered from token-frame spans. Confidence combines coverage, normalized token likelihood, and monotonic timestamp sanity. Synced chunks below 0.60 fall back locally to line timestamps. Plain-text chunks receive one additional MMS pass and then fail if still below threshold.

## 11. Enhanced LRC

The final timestamps are emitted as word-level inline tags and stored in `aligned.lrc`. The sidecar is copied beside the canonical MP3.

## 12. YouTube reference

The URL is requested manually after AI processing. No automatic search or URL validation is performed. `yt-dlp` extracts only audio. Librosa cross-correlation estimates the lag between the Spotify master and the YouTube audio.

## 13. Canonical artifact

The final MP3 is copied into `songs/`, tagged with ID3v2.4 standard fields, TXXX fields, USLT plain lyrics, SYLT word timestamps, and album artwork when available. Required custom frames are read back before commit.

## 14. Commit boundary

Only after the artifact and metadata pass verification does the code insert/update `songs.db`, mark `playlist.db` as `finished`, and remove the temporary workspace. Exceptions store their type, message, and traceback in `error_remark` and do not terminate the batch loop.

## 15. Important operational caveats

- CUDA availability is checked for MMS, but the configured production default remains CUDA. Demucs follows the configured device.
- External provider APIs can change. Provider errors are isolated where possible.
- CTC alignment timing depends on the loaded MMS model's output stride; the implementation uses the model's standard 20 ms frame assumption.
- Cross-correlation is optimized by downsampling to 8 kHz and limiting analysis windows. For unusually long tracks or complex intros, a second verification strategy may be desirable.
- The supplied specification says the final system yields “95% AI perfection”; that is an architectural target, not something code alone can guarantee without an evaluation corpus.
- The included `config.json` contains placeholders only. Credentials must be entered locally.
