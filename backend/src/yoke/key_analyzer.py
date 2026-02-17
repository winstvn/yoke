from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Krumhansl-Kessler key profiles
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_key_sync(path: Path) -> str | None:
    """Detect the musical key of an audio file (blocking)."""
    try:
        y, sr = librosa.load(str(path), sr=22050, mono=True, duration=60)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)

        best_corr = -2.0
        best_key = ""

        for shift in range(12):
            rolled = np.roll(chroma_mean, -shift)

            major_corr = float(np.corrcoef(rolled, _MAJOR_PROFILE)[0, 1])
            if major_corr > best_corr:
                best_corr = major_corr
                best_key = _KEY_NAMES[shift]

            minor_corr = float(np.corrcoef(rolled, _MINOR_PROFILE)[0, 1])
            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = f"{_KEY_NAMES[shift]}m"

        return best_key
    except Exception:
        logger.exception("Key detection failed for %s", path)
        return None


async def detect_key(path: Path) -> str | None:
    """Detect the musical key of an audio file (async wrapper)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _detect_key_sync, path)
