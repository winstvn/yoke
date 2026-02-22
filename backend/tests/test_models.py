import uuid
from yoke.models import (
    Singer,
    Song,
    QueueItem,
    PlaybackState,
    SessionSettings,
    SessionState,
)


def test_singer_creation():
    singer = Singer(name="Alice")
    assert singer.name == "Alice"
    assert singer.connected is True
    # id should be auto-generated
    uuid.UUID(singer.id)  # validates it's a UUID


def test_song_creation():
    song = Song(
        video_id="dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
        duration_seconds=212,
    )
    assert song.cached is False


def test_queue_item_creation():
    singer = Singer(name="Alice")
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )
    item = QueueItem(song=song, singer=singer)
    assert item.status == "waiting"
    uuid.UUID(item.id)


def test_playback_state_defaults():
    state = PlaybackState()
    assert state.status == "stopped"
    assert state.position_seconds == 0.0
    assert state.pitch_shift == 0


def test_pitch_shift_bounds():
    state = PlaybackState(pitch_shift=6)
    assert state.pitch_shift == 6
    state = PlaybackState(pitch_shift=-6)
    assert state.pitch_shift == -6


def test_session_settings_defaults():
    settings = SessionSettings()
    assert settings.host_id is None
    assert settings.anyone_can_reorder is False


def test_session_state_empty():
    state = SessionState()
    assert state.singers == []
    assert state.queue == []
    assert state.current is None
