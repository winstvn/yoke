from pathlib import Path

import pytest

from yoke.downloader import VideoDownloader


@pytest.fixture()
def tmp_video_dir(tmp_path: Path) -> Path:
    return tmp_path / "videos"


@pytest.fixture()
def downloader(tmp_video_dir: Path) -> VideoDownloader:
    d = VideoDownloader(video_dir=tmp_video_dir, max_concurrent=2)
    d.ensure_dir()
    return d


def test_video_path_returns_default_webm(
    downloader: VideoDownloader, tmp_video_dir: Path
) -> None:
    path = downloader.video_path("abc123")
    assert path.parent == tmp_video_dir
    assert path.name == "abc123.webm"


def test_video_path_finds_existing_file(
    downloader: VideoDownloader, tmp_video_dir: Path
) -> None:
    (tmp_video_dir / "abc123.mp4").write_text("fake video")
    path = downloader.video_path("abc123")
    assert path.parent == tmp_video_dir
    assert path.name == "abc123.mp4"


def test_is_cached_false(downloader: VideoDownloader) -> None:
    assert downloader.is_cached("nonexistent") is False


def test_is_cached_true(downloader: VideoDownloader, tmp_video_dir: Path) -> None:
    (tmp_video_dir / "abc123.webm").write_text("fake video")
    assert downloader.is_cached("abc123") is True


def test_creates_video_dir_on_ensure_dir(tmp_path: Path) -> None:
    video_dir = tmp_path / "new_videos"
    assert not video_dir.exists()
    d = VideoDownloader(video_dir=video_dir, max_concurrent=1)
    d.ensure_dir()
    assert video_dir.exists()
