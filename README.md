# TimeOSD

TimeOSD is a desktop tool for adding timestamp OSD to timelapse videos.

## Features (MVP)

- Load a video file and preview playback.
- Read base timestamp from file ctime (fallback) or manual input.
- Configure timelapse capture interval.
- Configure OSD style and position.
- Preview dynamic OSD in app.
- Export `.ass` subtitle and burn-in with FFmpeg.
- Optional NVENC encoding (`h264_nvenc`) with software fallback.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

Option 1 (recommended on Windows):

```bat
run_timeosd.bat
```

Option 2:

```powershell
python app.py
```

## Notes

- OSD refresh rate is capped at 5 updates/second.
- FFmpeg/FFprobe must be available in `PATH`.
