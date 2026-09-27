import numpy as np

from src.ctc_aligner import CTCForcedAligner
from src.types import TokenRef


def make_log_probs(labels: list[int], classes: int = 3) -> np.ndarray:
    out = np.full((len(labels), classes), -8.0, dtype=np.float32)
    for i, label in enumerate(labels):
        out[i, label] = -0.05
    return out


def test_simple_ctc_alignment():
    # blank, token 1, blank, token 2
    emissions = make_log_probs([0, 1, 1, 0, 2, 2])
    refs = [TokenRef(0, 1, 0, 0), TokenRef(1, 2, 0, 1)]
    result = CTCForcedAligner().align(emissions, refs, blank_id=0)
    assert len(result.spans) == 2
    assert result.spans[0].start_frame == 1
    assert result.spans[0].end_frame == 3
    assert result.spans[1].start_frame == 4
    assert result.spans[1].end_frame == 6


def test_repeated_label_requires_blank_transition():
    emissions = make_log_probs([0, 1, 1, 0, 1, 1])
    refs = [TokenRef(0, 1, 0, 0), TokenRef(1, 1, 0, 1)]
    result = CTCForcedAligner().align(emissions, refs, blank_id=0)
    assert len(result.spans) == 2
    assert result.spans[0].end_frame <= result.spans[1].start_frame
