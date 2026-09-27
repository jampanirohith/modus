import json
from pathlib import Path

import pytest

from src.json_manager import JSONManager


SAMPLE = Path("/mnt/data/001_Gelupu Thalupule_Mani Sharma, Sreerama Chandra.json")


def test_real_sample_json_is_cumulative_and_parseable():
    if not SAMPLE.exists():
        pytest.skip("Conversation sample JSON is not available in this environment")
    manager = JSONManager()
    data = manager.load(SAMPLE)
    assert isinstance(data, dict)
    assert "artwork" in data
    assert "lyrics" in data
    assert "playlist" in data
    assert "song" in data
    original = json.loads(json.dumps(data, ensure_ascii=False))
    final = manager.add_phase2(original, {"status": "test"})
    assert manager.non_phase2_equal(original, final)
