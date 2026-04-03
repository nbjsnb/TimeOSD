from __future__ import annotations

from pathlib import Path


def build_burn_command(
    ffmpeg_bin: str,
    input_video: Path,
    ass_file: Path,
    output_video: Path,
    use_nvenc: bool,
    keep_source_codec: bool = False,
    source_codec: str = "",
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
    cmd += _build_video_codec_args(
        use_nvenc=use_nvenc,
        keep_source_codec=keep_source_codec,
        source_codec=source_codec,
    )

    cmd += ["-c:a", "copy", str(output_video)]
    return cmd


def build_soft_mux_command(
    ffmpeg_bin: str,
    input_video: Path,
    ass_file: Path,
    output_video: Path,
    start_sec: float | None = None,
    duration_sec: float | None = None,
) -> list[str]:
    cmd: list[str] = [ffmpeg_bin, "-y"]

    if start_sec is not None and start_sec > 0:
        cmd += ["-ss", f"{start_sec:.3f}"]

    cmd += ["-i", str(input_video), "-i", str(ass_file)]

    if duration_sec is not None and duration_sec > 0:
        cmd += ["-t", f"{duration_sec:.3f}"]

    cmd += [
        "-map",
        "0",
        "-map",
        "1:0",
        "-c",
        "copy",
        "-c:s",
        "ass",
        "-disposition:s:0",
        "default",
        str(output_video),
    ]
    return cmd


def _build_video_codec_args(use_nvenc: bool, keep_source_codec: bool, source_codec: str) -> list[str]:
    codec_key = (source_codec or "").lower()

    if keep_source_codec:
        if codec_key in {"h264", "avc1"}:
            return _h264_encoder_args(use_nvenc)
        if codec_key in {"hevc", "h265", "hev1"}:
            return _hevc_encoder_args(use_nvenc)
        if codec_key in {"mpeg4"}:
            return ["-c:v", "mpeg4", "-q:v", "3"]

    return _h264_encoder_args(use_nvenc)


def _h264_encoder_args(use_nvenc: bool) -> list[str]:
    if use_nvenc:
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-cq",
            "22",
        ]
    return [
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
    ]


def _hevc_encoder_args(use_nvenc: bool) -> list[str]:
    if use_nvenc:
        return [
            "-c:v",
            "hevc_nvenc",
            "-preset",
            "p5",
            "-cq",
            "24",
        ]
    return [
        "-c:v",
        "libx265",
        "-crf",
        "24",
        "-preset",
        "medium",
    ]


def _escape_filter_filename(name: str) -> str:
    return name.replace("'", "\\'").replace(" ", "\\ ")
