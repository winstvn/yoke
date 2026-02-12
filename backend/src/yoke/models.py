from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class Singer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    connected: bool = True


class Song(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int
    cached: bool = False


class QueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    song: Song
    singer: Singer
    status: Literal["waiting", "downloading", "ready", "playing", "done"] = "waiting"


class PlaybackState(BaseModel):
    status: Literal["playing", "paused", "stopped"] = "stopped"
    position_seconds: float = 0.0
    pitch_shift: int = Field(default=0, ge=-6, le=6)


class SessionSettings(BaseModel):
    host_id: str | None = None
    anyone_can_reorder: bool = False


class SessionState(BaseModel):
    singers: list[Singer] = Field(default_factory=list)
    queue: list[QueueItem] = Field(default_factory=list)
    current: QueueItem | None = None
    playback: PlaybackState = Field(default_factory=PlaybackState)
    settings: SessionSettings = Field(default_factory=SessionSettings)
