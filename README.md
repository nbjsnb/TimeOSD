# TimeOSD

TimeOSD 是一个给视频补充时间戳 OSD（屏显）的桌面工具，重点面向运动相机缩时/增稳后无时间戳的后处理场景。

## 主要功能

- 加载视频并实时预览
- 读取视频元信息（时长、帧率、分辨率、视频编码）
- 支持缩时模式与正常速率模式
- 支持模板化时间文本（如 `{datetime}`）
- 支持样式调整与拖拽定位
- 生成 `.ass` 字幕并预览加载
- 支持导出 20 秒测试片与全片
- 支持 NVENC（`h264_nvenc` / `hevc_nvenc`）与 CPU 编码回退

## FFmpeg 依赖说明

本项目依赖 `ffmpeg` 和 `ffprobe`：

- `ffprobe` 用于读取视频元信息
- `ffmpeg` 用于烧录字幕或封装软字幕

请确保二者可在命令行直接运行（已加入 `PATH`），
或放在程序同目录。

FFmpeg 官网：

- https://ffmpeg.org/
- https://ffmpeg.org/download.html

## 分发版本说明

- `TimeOSD_onefile.exe`：标准单文件版，需要目标机可用 `ffmpeg/ffprobe`。
- `TimeOSD_onefile_portable.exe`：免安装单文件版，内置 `ffmpeg.exe` 和 `ffprobe.exe`。

## v1.1 新增

- 输出模式：硬字幕（重编码）/软字幕 MKV（不重编码）。
- 硬字幕支持“沿用原视频编码类型”（H.264/HEVC 自动映射）。
- 配置预设已包含输出模式、编码策略、NVENC、输出路径。
