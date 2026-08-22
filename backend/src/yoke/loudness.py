from __future__ import annotations

import asyncio
import json
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

# Most karaoke uploads sit at -9 to -11 LUFS, so this target attenuates more
# often than it boosts. Attenuation cannot clip.
TARGET_LUFS = -14.0

# Peaks stay this far below full scale after gain.
PEAK_CEILING_DBTP = -1.0

_MEASURE_TIMEOUT_SECONDS = 180.0


async def measure_loudness(path: Path) -> tuple[float | None, float | None]:
    """Measure integrated loudness (LUFS) and true peak (dBTP).

    Returns (None, None) if the file cannot be measured; callers read that as
    "apply no normalization". Decodes only -- nothing is re-encoded.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        logger.exception("Could not start ffmpeg to measure %s", path)
        return None, None

    try:
        _, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_MEASURE_TIMEOUT_SECONDS
        )
    except TimeoutError:
        logger.warning("Loudness measurement timed out for %s", path)
        proc.kill()
        return None, None

    if proc.returncode != 0:
        logger.warning("ffmpeg exited %s while measuring %s", proc.returncode, path)
        return None, None

    return _parse_loudnorm(stderr.decode("utf-8", errors="replace"), path)


def _parse_loudnorm(output: str, path: Path) -> tuple[float | None, float | None]:
    """Pull input_i/input_tp from loudnorm's JSON block on stderr."""
    start = output.rfind("{")
    end = output.rfind("}")
    if start == -1 or end == -1 or end < start:
        logger.warning("No loudnorm JSON found for %s", path)
        return None, None

    try:
        data = json.loads(output[start : end + 1])
        lufs = float(data["input_i"])
        peak = float(data["input_tp"])
    except (ValueError, KeyError, TypeError):
        logger.exception("Could not parse loudnorm output for %s", path)
        return None, None

    # A silent track reports -inf, which would give unbounded gain.
    if not (math.isfinite(lufs) and math.isfinite(peak)):
        logger.info("Non-finite loudness for %s (silent track?)", path)
        return None, None

    return lufs, peak
