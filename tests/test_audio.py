from pathlib import Path

from src.audio import AudioManager


class _Completed:
    returncode = 0
    stdout = ""


def test_decode_to_wav_keeps_wav_extension_for_ffmpeg_temp_file(tmp_path: Path, monkeypatch):
    source = tmp_path / "source.mp3"
    destination = tmp_path / "source_16k.wav"
    seen = {}

    monkeypatch.setattr("src.audio.require_binary", lambda name: "ffmpeg")

    def fake_run(command, **kwargs):
        seen["command"] = command
        tmp_path = Path(command[-1])
        assert tmp_path.suffix.lower() == ".wav"
        assert tmp_path.name.endswith(".wav")
        tmp_path.write_bytes(b"fake-wav")
        return _Completed()

    monkeypatch.setattr("src.audio.run_command", fake_run)
    result = AudioManager().decode_to_wav(source, destination)

    assert result == destination
    assert destination.read_bytes() == b"fake-wav"
    assert "-f" in seen["command"]
    assert seen["command"][seen["command"].index("-f") + 1] == "wav"


def test_decode_to_wav_cleanup_after_success(tmp_path: Path, monkeypatch):
    source = tmp_path / "source.mp3"
    destination = tmp_path / "source_16k.wav"
    source.write_bytes(b"source")

    monkeypatch.setattr("src.audio.require_binary", lambda name: "ffmpeg")

    temp_paths = []

    def fake_run(command, **kwargs):
        temp = Path(command[-1])
        temp_paths.append(temp)
        temp.write_bytes(b"wav")
        return _Completed()

    monkeypatch.setattr("src.audio.run_command", fake_run)
    AudioManager().decode_to_wav(source, destination)

    assert destination.exists()
    assert destination.read_bytes() == b"wav"
    assert temp_paths and not temp_paths[0].exists()
