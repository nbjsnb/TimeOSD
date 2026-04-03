from __future__ import annotations

from datetime import datetime, timedelta

from .models import TimeConfig


def real_elapsed_from_frame(frame_index: int, config: TimeConfig) -> timedelta:
    if frame_index < 0:
        frame_index = 0
    return timedelta(seconds=frame_index * config.capture_interval_sec)


def real_time_at_frame(frame_index: int, config: TimeConfig) -> datetime:
    return config.start_time + real_elapsed_from_frame(frame_index, config)


def real_time_at_media_seconds(media_seconds: float, video_fps: float, config: TimeConfig) -> datetime:
    frame_index = int(round(max(0.0, media_seconds) * max(0.0001, video_fps)))
    return real_time_at_frame(frame_index, config)
