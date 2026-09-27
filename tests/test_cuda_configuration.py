from pathlib import Path


def test_config_requires_cuda_by_default():
    import json
    cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
    assert cfg["runtime"]["device"] == "cuda"
    assert cfg["runtime"]["require_cuda"] is True
    assert cfg["runtime"]["allow_cpu_fallback"] is False


def test_requirements_pin_cuda_wheels():
    text = (Path(__file__).parents[1] / "requirements.txt").read_text(encoding="utf-8")
    assert "torch==2.9.1+cu128" in text
    assert "torchaudio==2.9.1+cu128" in text
    assert "download.pytorch.org/whl/cu128" in text


def test_pipeline_process_all_api_has_no_duplicate_cpu_fallback_argument():
    import inspect
    from src.pipeline import Pipeline
    params = inspect.signature(Pipeline.process_all).parameters
    assert "allow_cpu_fallback" not in params
