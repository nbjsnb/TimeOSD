# TimeOSD v1.2 Release Checklist

## 1. Version and Tag
- Version: `1.2`
- Git tag: `v1.2`

## 2. Rule for Binary Files
- Do not commit `.exe` files into the source repository.
- Upload built executables only as Release assets on the Git hosting platform.

## 3. Build Commands

Build no-FFmpeg package:
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile.spec
```

Build portable package (bundled ffmpeg/ffprobe):
```powershell
python -m PyInstaller --noconfirm TimeOSD_onefile_portable.spec
```

## 4. Release Assets (Upload to Release Page)
- `TimeOSD_v1.2_noffmpeg.exe`
- `TimeOSD_v1.2_portable.exe`

Suggested mapping:
- `dist\TimeOSD_onefile.exe` -> `TimeOSD_v1.2_noffmpeg.exe`
- `dist\TimeOSD_onefile_portable.exe` -> `TimeOSD_v1.2_portable.exe`

## 5. Release Notes (CN)
- 新增中英文双语界面切换（标题栏）
- 启动脚本新增 Python 环境检测
- 缺少 Python 时给出下载链接
- 缺少依赖时支持一键安装提示
- 交互文案与日志双语化

## 6. Release Notes (EN)
- Added bilingual UI switch in the title bar
- Added Python runtime check in startup script
- Shows Python download link when Python is missing
- Prompts for one-click dependency installation when dependencies are missing
- Added bilingual runtime messages and logs
