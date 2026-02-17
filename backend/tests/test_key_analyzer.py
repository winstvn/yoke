from pathlib import Path
from unittest.mock import patch

import numpy as np

from yoke.key_analyzer import _detect_key_sync, detect_key


def _make_sine_wav(path: Path, freq: float = 440.0, sr: int = 22050, duration: float = 2.0) -> None:
    """Write a mono WAV with a single sine tone."""
    import soundfile as sf

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * freq * t)
    sf.write(str(path), y, sr)


def test_detect_key_returns_string(tmp_path: Path) -> None:
    wav = tmp_path / "test.wav"
    _make_sine_wav(wav, freq=440.0)  # A4

    result = _detect_key_sync(wav)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) >= 1


def test_detect_key_returns_none_for_missing_file(tmp_path: Path) -> None:
    result = _detect_key_sync(tmp_path / "nonexistent.wav")
    assert result is None


async def test_detect_key_async(tmp_path: Path) -> None:
    wav = tmp_path / "test.wav"
    _make_sine_wav(wav, freq=440.0)

    result = await detect_key(wav)
    assert result is not None
    assert isinstance(result, str)
