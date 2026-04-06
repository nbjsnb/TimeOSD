# TimeOSD v1.2 Release Checklist

## 1. Version and Tag
- Version: `1.2`
- Git Tag: `v1.2`

## 2. Build Commands

Build no-FFmpeg package:
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```

Build portable package (with bundled ffmpeg/ffprobe):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```

## 3. Release Assets
- `TimeOSD_v1.2_noffmpeg.exe`
- `TimeOSD_v1.2_portable.exe`

Suggested mapping:
- `dist\TimeOSD_onefile.exe` -> `TimeOSD_v1.2_noffmpeg.exe`
- `dist\TimeOSD_onefile_portable.exe` -> `TimeOSD_v1.2_portable.exe`

## 4. Release Notes (CN)
- 新增中英文双语界面切换（标题栏）
- 启动脚本新增 Python 环境检测
- 缺少 Python 时给出下载链接
- 缺少依赖时支持一键安装提示
- 交互文案与日志双语化

## 5. Release Notes (EN)
- Added bilingual UI switch (title bar)
- Added Python runtime check in startup script
- Shows Python download link when Python is missing
- Prompts for one-click dependency installation when packages are missing
- Added bilingual runtime messages and logs
