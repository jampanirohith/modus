# Technical References and Implementation Notes

Research date: 2026-09-27.

## MMS

Hugging Face model card:

- `facebook/mms-1b-all`
- Telugu adapter code: `tel`
- language activation requires switching the tokenizer target language and loading the corresponding adapter.
- model license is shown as CC-BY-NC-4.0 on the current model card.

Reference: https://huggingface.co/facebook/mms-1b-all

## CTC forced alignment

The architectural distinction used by this project is:

```text
ASR decoding:
audio -> acoustic model -> predicted transcript + offsets

forced alignment:
audio -> acoustic model emissions
reference transcript -> tokenizer
emissions + reference -> CTC alignment path -> spans
```

Reference tutorial:
https://docs.pytorch.org/audio/main/tutorials/forced_alignment_for_multilingual_data_tutorial.html

This project implements its own reference-driven CTC Viterbi aligner to keep the alignment core independent of a deprecated convenience API.

## Demucs

Current Demucs packaging documents two-stem vocal separation, CUDA/CPU device selection, and segment sizing for memory control.

Reference: https://pypi.org/project/demucs/

## Silero VAD

The current package documents `load_silero_vad()` and `get_speech_timestamps()`, including tensor input and optional seconds output.

Reference: https://pypi.org/project/silero-vad/

## Mutagen / ID3

Mutagen exposes ID3 `SYLT` frames and millisecond timestamp mode. Phase 2 uses a dedicated descriptor so an existing synchronized lyric frame is not removed.

Reference: https://mutagen.readthedocs.io/en/latest/api/id3_frames.html

## Current dependency context

The plan deliberately pins a conservative compatibility stack rather than blindly taking the newest major versions. Current package pages at the research date showed materially newer releases for PyTorch, Transformers, librosa, SoundFile, Silero VAD, Mutagen, TorchCodec, and Demucs. The locked project stack should therefore be treated as a compatibility choice and upgraded only after dedicated regression tests.
