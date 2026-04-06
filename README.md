# TimeOSD

## 中文

### 项目简介
TimeOSD 是一个给视频叠加时间 OSD 的桌面工具，适用于延时摄影和运动相机素材后处理。

### v1.2 主要更新
- 中英文双语界面切换（标题栏）
- 启动脚本增加 Python 环境检测
- 缺少 Python 时给出下载链接
- 缺少依赖时提示是否自动安装

### 运行要求
- Windows 10/11
- Python 3.10+（源码运行）
- FFmpeg / FFprobe（使用不含依赖版 EXE 时需要）

### 源码运行
```powershell
python -m pip install -r requirements.txt
python app.py
```

或：
```bat
run_timeosd.bat
```

### EXE 打包

不含 FFmpeg（体积小，目标机需自行安装 FFmpeg）：
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```
输出：`dist\TimeOSD_onefile.exe`

含 FFmpeg（便携版）：
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```
输出：`dist\TimeOSD_onefile_portable.exe`

### v1.2 发布规范（重要）
- 不要把 `.exe` 提交到源码仓库。
- 二进制文件只在 Git 平台的 Release 页面上传。
- 推荐 tag：`v1.2`

### v1.2 Release 资产命名
- `TimeOSD_v1.2_noffmpeg.exe`（来自 `dist\TimeOSD_onefile.exe`）
- `TimeOSD_v1.2_portable.exe`（来自 `dist\TimeOSD_onefile_portable.exe`）

---

## English

### Overview
TimeOSD is a desktop tool that overlays timestamp OSD text onto videos, designed for timelapse and action-camera post-processing.

### What's New in v1.2
- Bilingual UI switch (Chinese/English) in the title bar
- Startup script now checks Python runtime
- Shows Python download link when Python is missing
- Prompts for dependency auto-installation when packages are missing

### Requirements
- Windows 10/11
- Python 3.10+ (for source run)
- FFmpeg / FFprobe (required for no-FFmpeg build)

### Run from Source
```powershell
python -m pip install -r requirements.txt
python app.py
```

or:
```bat
run_timeosd.bat
```

### Build EXE

Without FFmpeg (smaller, requires FFmpeg on target machine):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```
Output: `dist\TimeOSD_onefile.exe`

With FFmpeg bundled (portable):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```
Output: `dist\TimeOSD_onefile_portable.exe`

### v1.2 Release Policy (Important)
- Do not commit `.exe` binaries to the source repository.
- Upload binaries only as Release assets on your Git platform.
- Recommended tag: `v1.2`

### v1.2 Release Asset Names
- `TimeOSD_v1.2_noffmpeg.exe` (from `dist\TimeOSD_onefile.exe`)
- `TimeOSD_v1.2_portable.exe` (from `dist\TimeOSD_onefile_portable.exe`)
