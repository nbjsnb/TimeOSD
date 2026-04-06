# TimeOSD

## 中文说明

### 1. 项目简介
TimeOSD 是一个桌面工具，用于给视频叠加时间 OSD 字幕，面向延时摄影/运动相机素材的后处理场景。

### 2. v1.2 主要改进
- 界面支持中英文双语切换（标题栏快速切换）
- 启动脚本增加环境检测
- 未安装 Python 时给出下载链接
- 已安装 Python 但缺依赖时，提示是否自动安装

### 3. 核心功能
- 加载视频并实时预览
- 读取视频元信息（时长、帧率、分辨率、编码）
- 支持正常速率与间隔模式
- 支持模板化时间文本（如 `{datetime}`）
- 支持拖拽定位和样式调整
- 生成 `.ass` 字幕并预览
- 支持 20 秒测试导出和全片导出
- 支持硬字幕重编码与软字幕封装 MKV
- 支持 NVENC/CPU 编码及源编码类型保持策略

### 4. 运行要求
- Windows 10/11
- Python 3.10+（源码运行时）
- FFmpeg（`ffmpeg` / `ffprobe`）可用，或使用内置 FFmpeg 的便携版 EXE

### 5. 开发运行
```powershell
python -m pip install -r requirements.txt
python app.py
```

或直接运行：
```bat
run_timeosd.bat
```

### 6. EXE 打包

不包含 FFmpeg 依赖（体积更小，目标机需自行安装 FFmpeg）：
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```
输出：`dist\TimeOSD_onefile.exe`

包含 FFmpeg 依赖（便携版，开箱即用）：
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```
输出：`dist\TimeOSD_onefile_portable.exe`

### 7. v1.2 Release 建议资产
- `TimeOSD_v1.2_noffmpeg.exe`（由 `TimeOSD_onefile.exe` 重命名）
- `TimeOSD_v1.2_portable.exe`（由 `TimeOSD_onefile_portable.exe` 重命名）

建议 Tag：`v1.2`

---

## English

### 1. Overview
TimeOSD is a desktop app for overlaying timestamp OSD subtitles on videos, designed for timelapse/action-camera post-processing workflows.

### 2. What's New in v1.2
- Bilingual UI with quick Chinese/English switch in the title bar
- Startup script now checks runtime environment
- Shows Python download link when Python is missing
- Prompts to auto-install dependencies when Python exists but packages are missing

### 3. Core Features
- Video loading and real-time preview
- Video metadata probing (duration, fps, resolution, codec)
- Normal-speed mode and interval mode
- Template-based text rendering (for example `{datetime}`)
- Drag-and-drop positioning and style controls
- `.ass` subtitle generation and preview
- 20-second test export and full export
- Hard-sub re-encode and soft-sub MKV muxing
- NVENC/CPU encoding with source-codec preserving strategy

### 4. Requirements
- Windows 10/11
- Python 3.10+ (for source run)
- FFmpeg (`ffmpeg` / `ffprobe`) available, or use the portable EXE with bundled FFmpeg

### 5. Run from Source
```powershell
python -m pip install -r requirements.txt
python app.py
```

Or run:
```bat
run_timeosd.bat
```

### 6. Build EXE

Without bundled FFmpeg (smaller size, FFmpeg required on target machine):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```
Output: `dist\TimeOSD_onefile.exe`

With bundled FFmpeg (portable, out-of-box ready):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```
Output: `dist\TimeOSD_onefile_portable.exe`

### 7. Recommended v1.2 Release Assets
- `TimeOSD_v1.2_noffmpeg.exe` (renamed from `TimeOSD_onefile.exe`)
- `TimeOSD_v1.2_portable.exe` (renamed from `TimeOSD_onefile_portable.exe`)

Recommended tag: `v1.2`
