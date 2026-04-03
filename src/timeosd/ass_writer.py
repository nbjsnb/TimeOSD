from __future__ import annotations

from pathlib import Path

from .models import OsdStyle, TimeConfig
from .templating import render_template
from .time_engine import real_elapsed_from_frame, real_time_at_frame


def write_ass(
    output_path: Path,
    video_duration_sec: float,
    video_fps: float,
    play_res_x: int,
    play_res_y: int,
    time_cfg: TimeConfig,
    style: OsdStyle,
    template: str,
    per_frame_updates: bool = False,
) -> None:
    fps = max(0.0001, float(video_fps))
    updates_per_second = time_cfg.normalized_updates_per_second()
    step = (1.0 / fps) if per_frame_updates else (1.0 / updates_per_second)

    ass = []
    ass.append("[Script Info]")
    ass.append("ScriptType: v4.00+")
    ass.append(f"PlayResX: {max(16, int(play_res_x))}")
    ass.append(f"PlayResY: {max(16, int(play_res_y))}")
    ass.append("ScaledBorderAndShadow: yes")
    ass.append("")
    ass.append("[V4+ Styles]")
    ass.append(
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
        "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding"
    )

    alignment, margin_l, margin_r, margin_v = _ass_position(style)
    ass.append(
        "Style: OSD,"
        f"{style.font_name},{style.font_size},{_to_ass_color(style.color_hex)},&H000000FF,&H64000000,&H7F000000,"
        "0,0,0,0,100,100,0,0,1,"
        f"{style.outline},{style.shadow},{alignment},{margin_l},{margin_r},{margin_v},1"
    )
    ass.append("")
    ass.append("[Events]")
    ass.append("Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text")

    media_t = 0.0
    epsilon = 1e-6
    use_free_pos = style.anchor == "free"
    free_x = max(0, int(style.margin_x))
    free_y = max(0, int(style.margin_y))

    while media_t < video_duration_sec - epsilon:
        end_t = min(video_duration_sec, media_t + step)
        if end_t <= media_t + epsilon:
            break

        frame_index = int(round(media_t * fps))

        start = _ass_time(media_t)
        end = _ass_time(end_t)
        real_ts = real_time_at_frame(frame_index, time_cfg)
        elapsed_real = real_elapsed_from_frame(frame_index, time_cfg)
        text = render_template(template, real_ts, frame_index, elapsed_real)
        text = _escape_ass_text(text)

        if use_free_pos:
            # Use explicit absolute ASS position to minimize preview/export mismatch.
            text = f"{{\\an7\\pos({free_x},{free_y})}}" + text

        ass.append(f"Dialogue: 0,{start},{end},OSD,,0,0,0,,{text}")

        media_t += step

    output_path.write_text("\n".join(ass) + "\n", encoding="utf-8")


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    cs_total = int(round(seconds * 100))
    s_total, cs = divmod(cs_total, 100)
    m_total, s = divmod(s_total, 60)
    h, m = divmod(m_total, 60)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _to_ass_color(hex_color: str) -> str:
    c = hex_color.strip().lstrip("#")
    if len(c) != 6:
        c = "FFFFFF"
    r = c[0:2]
    g = c[2:4]
    b = c[4:6]
    return f"&H00{b}{g}{r}"


def _ass_position(style: OsdStyle) -> tuple[int, int, int, int]:
    anchor_map = {
        "top-left": 7,
        "top-center": 8,
        "top-right": 9,
        "middle-left": 4,
        "middle-center": 5,
        "middle-right": 6,
        "bottom-left": 1,
        "bottom-center": 2,
        "bottom-right": 3,
        "free": 7,
    }
    alignment = anchor_map.get(style.anchor, 3)

    if style.anchor == "free":
        # Free mode uses \pos(), margins are irrelevant in style.
        return 7, 0, 0, 0

    margin_l = style.margin_x if alignment in (1, 4, 7) else 20
    margin_r = style.margin_x if alignment in (3, 6, 9) else 20
    margin_v = style.margin_y
    return alignment, margin_l, margin_r, margin_v


def _escape_ass_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
