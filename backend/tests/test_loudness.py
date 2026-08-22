from pathlib import Path

from yoke.loudness import PEAK_CEILING_DBTP, TARGET_LUFS, _parse_loudnorm

_PATH = Path("/tmp/example.webm")


def _ffmpeg_output(input_i: str, input_tp: str) -> str:
    """Shape of what loudnorm writes to stderr, tabs and spacing included."""
    return (
        "[Parsed_loudnorm_0 @ 0xffff700044d0] \n"
        "{\n"
        f'\t"input_i" : "{input_i}",\n'
        f'\t"input_tp" : "{input_tp}",\n'
        '\t"input_lra" : "4.20",\n'
        '\t"input_thresh" : "-19.97",\n'
        '\t"normalization_type" : "dynamic"\n'
        "}\n"
        "[out#0/null @ 0xaaaad2e5eca0] video:2577KiB audio:150080KiB\n"
    )


def test_parses_integrated_loudness_and_peak():
    lufs, peak = _parse_loudnorm(_ffmpeg_output("-9.87", "1.00"), _PATH)
    assert lufs == -9.87
    assert peak == 1.00


def test_parses_quiet_track():
    lufs, peak = _parse_loudnorm(_ffmpeg_output("-27.64", "-11.86"), _PATH)
    assert lufs == -27.64
    assert peak == -11.86


def test_silent_track_is_unmeasurable():
    """-inf would otherwise produce an unbounded gain."""
    assert _parse_loudnorm(_ffmpeg_output("-inf", "-inf"), _PATH) == (None, None)


def test_missing_json_returns_none():
    assert _parse_loudnorm("ffmpeg: Invalid data found\n", _PATH) == (None, None)


def test_malformed_json_returns_none():
    assert _parse_loudnorm("{ not json at all }", _PATH) == (None, None)


def test_missing_keys_return_none():
    assert _parse_loudnorm('{"input_lra" : "4.2"}', _PATH) == (None, None)


def test_target_leaves_headroom_for_typical_uploads():
    """A -14 target attenuates the loud uploads that cause the problem."""
    assert TARGET_LUFS < -9.0
    assert PEAK_CEILING_DBTP < 0.0
