from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class OsdStyle:
    font_name: str = "Arial"
    font_size: int = 36
    color_hex: str = "#FFFFFF"
    outline: int = 2
    shadow: int = 1
    margin_x: int = 32
    margin_y: int = 32
    anchor: str = "bottom-right"


@dataclass(slots=True)
class TimeConfig:
    start_time: datetime
    capture_interval_sec: float
    updates_per_second: int = 1

    def normalized_updates_per_second(self) -> int:
        # Product requirement: maximum 5 updates per second.
        return max(1, min(5, int(self.updates_per_second)))
