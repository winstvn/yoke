from unittest.mock import MagicMock, patch

from yoke.youtube import _parse_results, search_youtube


def _make_entry(video_id: str, title: str, duration: int) -> dict:
    return {
        "id": video_id,
        "title": title,
        "duration": duration,
        "thumbnails": [{"url": f"https://i.ytimg.com/vi/{video_id}/default.jpg"}],
    }


def test_parse_results():
    data = {
        "entries": [
            _make_entry("abc123", "Test Song", 180),
            _make_entry("def456", "Another Song", 240),
        ]
    }
    results = _parse_results(data)
    assert len(results) == 2

    assert results[0].video_id == "abc123"
    assert results[0].title == "Test Song"
    assert results[0].thumbnail_url == "https://i.ytimg.com/vi/abc123/default.jpg"
    assert results[0].duration_seconds == 180

    assert results[1].video_id == "def456"
    assert results[1].title == "Another Song"
    assert results[1].thumbnail_url == "https://i.ytimg.com/vi/def456/default.jpg"
    assert results[1].duration_seconds == 240


def test_parse_results_handles_missing_entries():
    assert _parse_results(None) == []
    assert _parse_results({}) == []
    assert _parse_results({"entries": None}) == []


def test_parse_results_skips_entries_without_id():
    data = {
        "entries": [
            _make_entry("abc123", "Valid Song", 180),
            {"title": "No ID Song", "duration": 120, "thumbnails": []},
            _make_entry("def456", "Another Valid", 200),
        ]
    }
    results = _parse_results(data)
    assert len(results) == 2
    assert results[0].video_id == "abc123"
    assert results[1].video_id == "def456"


async def test_search_youtube():
    fake_data = {
        "entries": [
            _make_entry("vid1", "Result One", 300),
        ]
    }

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = fake_data
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)

    with patch("yoke.youtube.yt_dlp.YoutubeDL", return_value=mock_ydl_instance):
        results = await search_youtube("test query", max_results=5)

    assert len(results) == 1
    assert results[0].video_id == "vid1"
    assert results[0].title == "Result One"

    mock_ydl_instance.extract_info.assert_called_once_with(
        "ytsearch5:test query", download=False
    )
