from __future__ import annotations

from datetime import datetime, timedelta


def render_template(template: str, ts: datetime, frame_index: int, elapsed_real: timedelta) -> str:
    mapping = {
        "date": ts.strftime("%Y-%m-%d"),
        "time": ts.strftime("%H:%M:%S"),
        "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "frame": str(frame_index),
        "elapsed_real": _format_timedelta(elapsed_real),
    }
    out = template
    for key, value in mapping.items():
        out = out.replace("{" + key + "}", value)
    return out


def _format_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
