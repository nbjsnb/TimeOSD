from __future__ import annotations

from pathlib import Path


def build_burn_command(
    ffmpeg_bin: str,
    input_video: Path,
    ass_file: Path,
    output_video: Path,
    use_nvenc: bool,
    start_sec: float | None = None,
    duration_sec: float | None = None,
) -> list[str]:
    vf = f"ass={_escape_filter_filename(ass_file.name)}"
    cmd: list[str] = [ffmpeg_bin, "-y"]

    if start_sec is not None and start_sec > 0:
        cmd += ["-ss", f"{start_sec:.3f}"]

    cmd += ["-i", str(input_video)]

    if duration_sec is not None and duration_sec > 0:
        cmd += ["-t", f"{duration_sec:.3f}"]

    cmd += ["-vf", vf]

    if use_nvenc:
        cmd += [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-cq",
            "22",
        ]
    else:
        cmd += [
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
        ]

    cmd += ["-c:a", "copy", str(output_video)]
    return cmd


def _escape_filter_filename(name: str) -> str:
    return name.replace("'", "\\'").replace(" ", "\\ ")
