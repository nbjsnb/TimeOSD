from __future__ import annotations

import json
import re
import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from .ass_writer import write_ass
from .ffmpeg_ops import build_burn_command, build_soft_mux_command
from .models import OsdStyle, TimeConfig
from .templating import render_template
from .time_engine import real_elapsed_from_frame, real_time_at_frame


class PreviewView(QGraphicsView):
    def __init__(self, owner: "MainWindow", parent=None):
        super().__init__(parent)
        self.owner = owner

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.owner.fit_scene_to_view()
        self.owner.place_overlay_text()


class DraggableTextItem(QGraphicsTextItem):
    def __init__(self, owner: "MainWindow", text: str):
        super().__init__(text)
        self.owner = owner
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.owner.on_overlay_item_moved(value)
        return super().itemChange(change, value)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TimeOSD")
        self.resize(1400, 860)

        self.video_path: Path | None = None
        self.video_duration_sec: float = 0.0
        self.video_fps: float = 30.0
        self.video_width: int = 1920
        self.video_height: int = 1080
        self.video_codec: str = "unknown"
        self.generated_ass_path: Path | None = None
        self.ffmpeg_bin = resolve_tool_binary("ffmpeg")
        self.ffprobe_bin = resolve_tool_binary("ffprobe")

        self.preset_file = Path(__file__).resolve().parents[2] / "timeosd_presets.json"
        self.presets: dict[str, dict] = {}

        self.ass_preview_events: list[tuple[float, float, str]] = []
        self.ass_preview_cursor: int = 0
        self.last_media_sec: float = -1.0

        self.user_dragging_slider = False
        self.suppress_overlay_move_event = False
        self.suppress_mode_toggle = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.append_process_output)
        self.process.readyReadStandardError.connect(self.append_process_output)
        self.process.finished.connect(self.on_process_finished)

        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self.update_preview_text)
        self.preview_timer.start()

        self.build_ui()
        self.load_presets_from_disk()

    def build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        grid = QGridLayout(root)

        left_box = QGroupBox("视频预览")
        left_layout = QVBoxLayout(left_box)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, self.video_width, self.video_height)

        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(self.scene.sceneRect().size())
        self.scene.addItem(self.video_item)
        self.player.setVideoOutput(self.video_item)

        self.overlay_item = DraggableTextItem(self, "OSD 预览")
        self.overlay_item.document().setDocumentMargin(0)
        self.overlay_item.setZValue(10)
        self.scene.addItem(self.overlay_item)

        self.preview_view = PreviewView(self, left_box)
        self.preview_view.setScene(self.scene)
        self.preview_view.setMinimumSize(900, 560)

        timeline_row = QHBoxLayout()
        self.lbl_time_current = QLabel("00:00:00")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.lbl_time_total = QLabel("00:00:00")
        timeline_row.addWidget(self.lbl_time_current)
        timeline_row.addWidget(self.slider)
        timeline_row.addWidget(self.lbl_time_total)

        btn_row = QHBoxLayout()
        self.btn_open = QPushButton("加载视频")
        self.btn_play = QPushButton("播放/暂停")
        self.btn_probe = QPushButton("刷新元信息")
        self.btn_export_20s = QPushButton("导出20秒测试")
        self.btn_export = QPushButton("导出并渲染")
        for b in [self.btn_open, self.btn_play, self.btn_probe, self.btn_export_20s, self.btn_export]:
            btn_row.addWidget(b)

        left_layout.addWidget(self.preview_view)
        left_layout.addLayout(timeline_row)
        left_layout.addLayout(btn_row)

        right_box = QGroupBox("参数设置")
        form = QFormLayout(right_box)

        self.edit_start = QDateTimeEdit(datetime.now())
        self.edit_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.edit_start.setCalendarPopup(True)

        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.01, 3600.0)
        self.spin_interval.setValue(1.0)
        self.spin_interval.setDecimals(3)

        self.chk_normal_speed = QCheckBox("正常速率视频(1秒=1秒)")
        self.chk_normal_speed.setChecked(False)

        self.spin_ups = QSpinBox()
        self.spin_ups.setRange(1, 5)
        self.spin_ups.setValue(5)

        self.chk_per_frame_ass = QCheckBox("ASS按帧更新(文件更大，导出更慢)")
        self.chk_per_frame_ass.setChecked(False)

        self.edit_template = QLineEdit("{datetime}")

        self.combo_anchor = QComboBox()
        self.combo_anchor.addItems(
            [
                "top-left",
                "top-center",
                "top-right",
                "middle-left",
                "middle-center",
                "middle-right",
                "bottom-left",
                "bottom-center",
                "bottom-right",
                "free",
            ]
        )
        self.combo_anchor.setCurrentText("bottom-right")

        self.spin_font = QSpinBox()
        self.spin_font.setRange(12, 160)
        self.spin_font.setValue(36)

        self.edit_color = QLineEdit("#FFFFFF")

        self.spin_margin_x = QSpinBox()
        self.spin_margin_x.setRange(0, 10000)
        self.spin_margin_x.setValue(32)

        self.spin_margin_y = QSpinBox()
        self.spin_margin_y.setRange(0, 10000)
        self.spin_margin_y.setValue(32)

        self.chk_use_ass_preview = QCheckBox("优先使用已加载ASS字幕预览")
        self.chk_use_ass_preview.setChecked(False)

        self.combo_export_mode = QComboBox()
        self.combo_export_mode.addItems(["硬字幕(重新编码)", "软字幕封装MKV(不重编码)"])
        self.combo_export_mode.setCurrentIndex(0)

        self.chk_keep_source_codec = QCheckBox("硬字幕沿用原视频编码类型")
        self.chk_keep_source_codec.setChecked(True)

        self.chk_nvenc = QCheckBox("使用 NVENC")
        self.chk_nvenc.setChecked(True)

        self.edit_output = QLineEdit()

        subtitle_btn_row = QWidget()
        subtitle_btn_layout = QHBoxLayout(subtitle_btn_row)
        subtitle_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_generate_ass = QPushButton("生成字幕(ASS)")
        self.btn_load_ass_preview = QPushButton("加载字幕预览")
        subtitle_btn_layout.addWidget(self.btn_generate_ass)
        subtitle_btn_layout.addWidget(self.btn_load_ass_preview)

        preset_row = QWidget()
        preset_layout = QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_preset = QComboBox()
        self.btn_preset_save = QPushButton("保存配置")
        self.btn_preset_load = QPushButton("加载配置")
        self.btn_preset_delete = QPushButton("删除配置")
        preset_layout.addWidget(self.combo_preset)
        preset_layout.addWidget(self.btn_preset_save)
        preset_layout.addWidget(self.btn_preset_load)
        preset_layout.addWidget(self.btn_preset_delete)

        form.addRow("起始时间", self.edit_start)
        form.addRow("时间模式", self.chk_normal_speed)
        form.addRow("拍摄间隔(秒)", self.spin_interval)
        form.addRow("字幕更新频率(次/秒, 最大5)", self.spin_ups)
        form.addRow("ASS导出模式", self.chk_per_frame_ass)
        form.addRow("文本模板", self.edit_template)
        form.addRow("位置锚点", self.combo_anchor)
        form.addRow("字体大小", self.spin_font)
        form.addRow("字体颜色", self.edit_color)
        form.addRow("水平边距", self.spin_margin_x)
        form.addRow("垂直边距", self.spin_margin_y)
        form.addRow("字幕文件操作", subtitle_btn_row)
        form.addRow("输出模式", self.combo_export_mode)
        form.addRow("硬字幕编码", self.chk_keep_source_codec)
        form.addRow("编码器", self.chk_nvenc)
        form.addRow("输出视频路径", self.edit_output)
        form.addRow("预览模式", self.chk_use_ass_preview)
        form.addRow("—— 配置管理 ——", QLabel("保存/加载/删除预设"))
        form.addRow("配置预设", preset_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)

        grid.addWidget(left_box, 0, 0)
        grid.addWidget(right_box, 0, 1)
        grid.addWidget(self.log, 1, 0, 1, 2)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 2)
        grid.setRowStretch(0, 3)
        grid.setRowStretch(1, 1)

        self.btn_open.clicked.connect(self.on_open_video)
        self.btn_play.clicked.connect(self.on_play_pause)
        self.btn_probe.clicked.connect(self.on_probe)
        self.btn_generate_ass.clicked.connect(self.on_generate_ass)
        self.btn_load_ass_preview.clicked.connect(self.on_load_ass_preview)
        self.btn_preset_save.clicked.connect(self.on_save_preset)
        self.btn_preset_load.clicked.connect(self.on_load_preset)
        self.btn_preset_delete.clicked.connect(self.on_delete_preset)
        self.btn_export_20s.clicked.connect(self.on_export_20s)
        self.btn_export.clicked.connect(self.on_export_full)

        self.combo_export_mode.currentIndexChanged.connect(self.on_export_mode_changed)

        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)

        for signal in [
            self.edit_template.textChanged,
            self.spin_font.valueChanged,
            self.edit_color.textChanged,
            self.spin_margin_x.valueChanged,
            self.spin_margin_y.valueChanged,
            self.combo_anchor.currentTextChanged,
            self.spin_interval.valueChanged,
            self.chk_normal_speed.toggled,
            self.edit_start.dateTimeChanged,
            self.chk_use_ass_preview.toggled,
        ]:
            signal.connect(self.update_preview_text)

        self.chk_per_frame_ass.toggled.connect(self.on_per_frame_toggled)
        self.chk_normal_speed.toggled.connect(self.on_normal_speed_toggled)
        self.on_per_frame_toggled(self.chk_per_frame_ass.isChecked())
        self.on_normal_speed_toggled(self.chk_normal_speed.isChecked())
        self.on_export_mode_changed(self.combo_export_mode.currentIndex())

        self.apply_overlay_style()
        self.fit_scene_to_view()
        self.place_overlay_text()

    def on_per_frame_toggled(self, checked: bool) -> None:
        if checked and self.chk_normal_speed.isChecked() and not self.suppress_mode_toggle:
            self.suppress_mode_toggle = True
            self.chk_normal_speed.setChecked(False)
            self.suppress_mode_toggle = False
            self.log.appendPlainText("已关闭‘正常速率视频’，因为‘ASS按帧更新’与其互斥。")
        self.spin_ups.setEnabled(not checked)

    def on_normal_speed_toggled(self, checked: bool) -> None:
        if checked and self.chk_per_frame_ass.isChecked() and not self.suppress_mode_toggle:
            self.suppress_mode_toggle = True
            self.chk_per_frame_ass.setChecked(False)
            self.suppress_mode_toggle = False
            self.log.appendPlainText("已关闭‘ASS按帧更新’，因为‘正常速率视频’与其互斥。")
        self.spin_interval.setEnabled(not checked)
        if checked:
            self.log.appendPlainText("已启用正常速率模式: 拍摄间隔参数将被忽略。")

    def on_export_mode_changed(self, _index: int) -> None:
        is_hard = self.combo_export_mode.currentIndex() == 0
        self.chk_keep_source_codec.setEnabled(is_hard)
        self.chk_nvenc.setEnabled(is_hard)

        cur = self.edit_output.text().strip()
        if not cur:
            return
        out = Path(cur)
        target_suffix = ".mp4" if is_hard else ".mkv"
        if out.suffix.lower() != target_suffix:
            out = out.with_suffix(target_suffix)
            self.edit_output.setText(str(out))

    def load_presets_from_disk(self) -> None:
        if not self.preset_file.exists():
            self.presets = {}
            self.refresh_preset_combo()
            return
        try:
            data = json.loads(self.preset_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.presets = data
            else:
                self.presets = {}
        except Exception as ex:
            self.presets = {}
            self.log.appendPlainText(f"读取配置文件失败: {ex}")
        self.refresh_preset_combo()

    def save_presets_to_disk(self) -> None:
        self.preset_file.write_text(json.dumps(self.presets, ensure_ascii=False, indent=2), encoding="utf-8")

    def refresh_preset_combo(self) -> None:
        current = self.combo_preset.currentText() if hasattr(self, "combo_preset") else ""
        self.combo_preset.clear()
        for name in sorted(self.presets.keys()):
            self.combo_preset.addItem(name)
        if current and current in self.presets:
            self.combo_preset.setCurrentText(current)

    def collect_current_config(self) -> dict:
        return {
            "start_time": self.edit_start.dateTime().toPython().isoformat(sep=" "),
            "normal_speed": self.chk_normal_speed.isChecked(),
            "interval": float(self.spin_interval.value()),
            "updates_per_second": int(self.spin_ups.value()),
            "per_frame_ass": self.chk_per_frame_ass.isChecked(),
            "template": self.edit_template.text(),
            "anchor": self.combo_anchor.currentText(),
            "font_size": int(self.spin_font.value()),
            "color": self.edit_color.text().strip(),
            "margin_x": int(self.spin_margin_x.value()),
            "margin_y": int(self.spin_margin_y.value()),
            "use_ass_preview": self.chk_use_ass_preview.isChecked(),
            "export_mode": int(self.combo_export_mode.currentIndex()),
            "keep_source_codec": self.chk_keep_source_codec.isChecked(),
            "nvenc": self.chk_nvenc.isChecked(),
            "output_path": self.edit_output.text().strip(),
        }

    def apply_config(self, cfg: dict) -> None:
        try:
            if "start_time" in cfg:
                dt = datetime.fromisoformat(str(cfg["start_time"]))
                self.edit_start.setDateTime(dt)
        except Exception:
            pass

        self.chk_normal_speed.setChecked(bool(cfg.get("normal_speed", self.chk_normal_speed.isChecked())))
        self.spin_interval.setValue(float(cfg.get("interval", self.spin_interval.value())))
        self.spin_ups.setValue(int(cfg.get("updates_per_second", self.spin_ups.value())))
        self.chk_per_frame_ass.setChecked(bool(cfg.get("per_frame_ass", self.chk_per_frame_ass.isChecked())))
        self.edit_template.setText(str(cfg.get("template", self.edit_template.text())))

        anchor = str(cfg.get("anchor", self.combo_anchor.currentText()))
        if self.combo_anchor.findText(anchor) >= 0:
            self.combo_anchor.setCurrentText(anchor)

        self.spin_font.setValue(int(cfg.get("font_size", self.spin_font.value())))
        self.edit_color.setText(str(cfg.get("color", self.edit_color.text())))
        self.spin_margin_x.setValue(int(cfg.get("margin_x", self.spin_margin_x.value())))
        self.spin_margin_y.setValue(int(cfg.get("margin_y", self.spin_margin_y.value())))
        self.chk_use_ass_preview.setChecked(bool(cfg.get("use_ass_preview", self.chk_use_ass_preview.isChecked())))
        self.combo_export_mode.setCurrentIndex(int(cfg.get("export_mode", self.combo_export_mode.currentIndex())))
        self.chk_keep_source_codec.setChecked(bool(cfg.get("keep_source_codec", self.chk_keep_source_codec.isChecked())))
        self.chk_nvenc.setChecked(bool(cfg.get("nvenc", self.chk_nvenc.isChecked())))
        if cfg.get("output_path"):
            self.edit_output.setText(str(cfg.get("output_path")))

        self.update_preview_text()

    def on_save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "保存配置", "请输入配置名称:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "名称为空", "请输入有效的配置名称。")
            return
        self.presets[name] = self.collect_current_config()
        self.save_presets_to_disk()
        self.refresh_preset_combo()
        self.combo_preset.setCurrentText(name)
        self.log.appendPlainText(f"配置已保存: {name} -> {self.preset_file}")

    def on_load_preset(self) -> None:
        name = self.combo_preset.currentText().strip()
        if not name:
            QMessageBox.warning(self, "未选择配置", "请先选择一个配置。")
            return
        cfg = self.presets.get(name)
        if not isinstance(cfg, dict):
            QMessageBox.warning(self, "配置不存在", "选择的配置无效。")
            return
        self.apply_config(cfg)
        self.log.appendPlainText(f"已加载配置: {name}")

    def on_delete_preset(self) -> None:
        name = self.combo_preset.currentText().strip()
        if not name:
            QMessageBox.warning(self, "未选择配置", "请先选择一个配置。")
            return
        reply = QMessageBox.question(self, "删除配置", f"确认删除配置: {name} ?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        if name in self.presets:
            del self.presets[name]
            self.save_presets_to_disk()
            self.refresh_preset_combo()
            self.log.appendPlainText(f"已删除配置: {name}")

    def fit_scene_to_view(self) -> None:
        self.preview_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def on_overlay_item_moved(self, value) -> None:
        if self.suppress_overlay_move_event:
            return
        if self.combo_anchor.currentText() != "free":
            self.combo_anchor.setCurrentText("free")
        x = int(round(max(0.0, value.x())))
        y = int(round(max(0.0, value.y())))
        self.spin_margin_x.setValue(min(self.spin_margin_x.maximum(), x))
        self.spin_margin_y.setValue(min(self.spin_margin_y.maximum(), y))

    def on_open_video(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频",
            "",
            "视频文件 (*.mp4 *.mov *.mkv *.avi);;所有文件 (*)",
        )
        if not file_path:
            return

        self.video_path = Path(file_path)
        self.player.setSource(QUrl.fromLocalFile(str(self.video_path)))

        out = self.video_path.with_name(self.video_path.stem + "_osd.mp4")
        self.edit_output.setText(str(out))
        self.on_export_mode_changed(self.combo_export_mode.currentIndex())
        self.generated_ass_path = out.with_suffix(".ass")

        ctime = datetime.fromtimestamp(self.video_path.stat().st_ctime)
        self.edit_start.setDateTime(ctime)

        self.ass_preview_events.clear()
        self.ass_preview_cursor = 0
        self.last_media_sec = -1.0
        self.chk_use_ass_preview.setChecked(False)

        self.on_probe()
        self.update_preview_text()
        self.log.appendPlainText(f"已加载视频: {self.video_path}")

    def on_play_pause(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_probe(self) -> None:
        if not self.video_path:
            return
        if not self.ffprobe_bin:
            self.log.appendPlainText("未找到 ffprobe：请安装 FFmpeg，或将 ffprobe.exe 放到程序目录。")
            QMessageBox.warning(
                self,
                "缺少 FFprobe",
                "未找到 ffprobe。\n请安装 FFmpeg 并加入 PATH，或把 ffprobe.exe 放到程序同目录。",
            )
            return
        try:
            duration, fps, width, height, codec = probe_video(self.video_path, self.ffprobe_bin)
            self.video_duration_sec = duration
            self.video_fps = fps if fps > 0 else 30.0
            self.video_width = max(16, width)
            self.video_height = max(16, height)
            self.video_codec = codec or "unknown"

            self.scene.setSceneRect(0, 0, self.video_width, self.video_height)
            self.video_item.setSize(self.scene.sceneRect().size())
            self.spin_margin_x.setMaximum(max(10000, self.video_width * 2))
            self.spin_margin_y.setMaximum(max(10000, self.video_height * 2))
            self.fit_scene_to_view()
            self.place_overlay_text()

            self.log.appendPlainText(
                f"视频信息: 时长={self.video_duration_sec:.3f}s, 帧率={self.video_fps:.3f}, 分辨率={self.video_width}x{self.video_height}, 编码={self.video_codec}"
            )
        except Exception as ex:
            self.log.appendPlainText(f"读取元信息失败: {ex}")

    def on_generate_ass(self) -> None:
        if not self.video_path:
            QMessageBox.warning(self, "未加载视频", "请先加载视频。")
            return

        output_text = self.edit_output.text().strip()
        if not output_text:
            QMessageBox.warning(self, "未设置输出", "请先设置输出视频路径。")
            return

        output_path = Path(output_text)
        ass_path = output_path.with_suffix(".ass")

        if self.video_duration_sec <= 0.0:
            self.on_probe()

        cfg = self.build_time_config()
        style = self.build_style()

        write_ass(
            output_path=ass_path,
            video_duration_sec=self.video_duration_sec,
            video_fps=self.video_fps,
            play_res_x=self.video_width,
            play_res_y=self.video_height,
            time_cfg=cfg,
            style=style,
            template=self.edit_template.text(),
            per_frame_updates=self.chk_per_frame_ass.isChecked(),
        )
        self.generated_ass_path = ass_path
        self.log.appendPlainText(f"已生成字幕(会覆盖同名文件): {ass_path}")

    def on_load_ass_preview(self) -> None:
        default = str(self.generated_ass_path) if self.generated_ass_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择ASS字幕",
            default,
            "ASS 字幕 (*.ass);;所有文件 (*)",
        )
        if not file_path:
            return

        ass_path = Path(file_path)
        try:
            events = parse_ass_events(ass_path)
            if not events:
                raise ValueError("字幕文件未解析到任何对话事件")
            self.ass_preview_events = events
            self.ass_preview_cursor = 0
            self.last_media_sec = -1.0
            self.chk_use_ass_preview.setChecked(True)
            self.log.appendPlainText(f"已加载字幕预览: {ass_path} (事件数: {len(events)})")
            self.update_preview_text()
        except Exception as ex:
            self.log.appendPlainText(f"加载字幕失败: {ex}")
            QMessageBox.warning(self, "加载失败", str(ex))

    def on_export_20s(self) -> None:
        self.export_video(preview_20s=True)

    def on_export_full(self) -> None:
        self.export_video(preview_20s=False)

    def export_video(self, preview_20s: bool) -> None:
        if not self.video_path:
            QMessageBox.warning(self, "未加载视频", "请先加载视频。")
            return

        output_text = self.edit_output.text().strip()
        if not output_text:
            QMessageBox.warning(self, "未设置输出", "请先设置输出视频路径。")
            return

        output_path = Path(output_text)
        is_hard_sub = self.combo_export_mode.currentIndex() == 0
        target_suffix = ".mp4" if is_hard_sub else ".mkv"
        if output_path.suffix.lower() != target_suffix:
            output_path = output_path.with_suffix(target_suffix)
            self.edit_output.setText(str(output_path))

        if preview_20s:
            output_path = output_path.with_name(output_path.stem + "_preview20s" + output_path.suffix)

        ass_path = output_path.with_suffix(".ass")

        if self.video_duration_sec <= 0.0:
            self.on_probe()
        if not self.ffmpeg_bin:
            self.log.appendPlainText("未找到 ffmpeg：请安装 FFmpeg，或将 ffmpeg.exe 放到程序目录。")
            QMessageBox.warning(
                self,
                "缺少 FFmpeg",
                "未找到 ffmpeg。\n请安装 FFmpeg 并加入 PATH，或把 ffmpeg.exe 放到程序同目录。",
            )
            return

        cfg = self.build_time_config()
        style = self.build_style()

        ass_duration = min(20.0, max(0.1, self.video_duration_sec)) if preview_20s else self.video_duration_sec
        write_ass(
            output_path=ass_path,
            video_duration_sec=ass_duration,
            video_fps=self.video_fps,
            play_res_x=self.video_width,
            play_res_y=self.video_height,
            time_cfg=cfg,
            style=style,
            template=self.edit_template.text(),
            per_frame_updates=self.chk_per_frame_ass.isChecked(),
        )

        start_sec = 0.0 if preview_20s else None
        duration_sec = 20.0 if preview_20s else None

        if is_hard_sub:
            cmd = build_burn_command(
                ffmpeg_bin=self.ffmpeg_bin,
                input_video=self.video_path,
                ass_file=ass_path,
                output_video=output_path,
                use_nvenc=self.chk_nvenc.isChecked(),
                keep_source_codec=self.chk_keep_source_codec.isChecked(),
                source_codec=self.video_codec,
                start_sec=start_sec,
                duration_sec=duration_sec,
            )
        else:
            cmd = build_soft_mux_command(
                ffmpeg_bin=self.ffmpeg_bin,
                input_video=self.video_path,
                ass_file=ass_path,
                output_video=output_path,
                start_sec=start_sec,
                duration_sec=duration_sec,
            )

        label = "开始导出20秒测试" if preview_20s else "开始导出全片"
        self.log.appendPlainText(f"{label}: " + " ".join(cmd))
        self.btn_export.setEnabled(False)
        self.btn_export_20s.setEnabled(False)
        self.process.setWorkingDirectory(str(ass_path.parent))
        self.process.start(cmd[0], cmd[1:])

    def on_position_changed(self, pos_ms: int) -> None:
        if not self.user_dragging_slider:
            self.slider.setValue(pos_ms)
            self.lbl_time_current.setText(format_hhmmss(pos_ms / 1000.0))

    def on_duration_changed(self, dur_ms: int) -> None:
        self.slider.setRange(0, max(0, dur_ms))
        self.lbl_time_total.setText(format_hhmmss(dur_ms / 1000.0))

    def on_slider_pressed(self) -> None:
        self.user_dragging_slider = True

    def on_slider_released(self) -> None:
        self.user_dragging_slider = False
        self.player.setPosition(self.slider.value())
        self.update_preview_text()

    def on_slider_moved(self, value: int) -> None:
        self.lbl_time_current.setText(format_hhmmss(value / 1000.0))
        self.player.setPosition(value)
        self.update_preview_text()

    def update_preview_text(self) -> None:
        if not self.video_path:
            self.overlay_item.setPlainText("OSD 预览")
            self.place_overlay_text()
            return

        media_sec = max(0.0, self.player.position() / 1000.0)
        frame_index = int(round(media_sec * self.video_fps))
        cfg = self.build_time_config()

        text = ""
        if self.chk_use_ass_preview.isChecked() and self.ass_preview_events:
            text = self.get_ass_preview_text(media_sec)
        if not text:
            ts = real_time_at_frame(frame_index, cfg)
            elapsed = real_elapsed_from_frame(frame_index, cfg)
            text = render_template(self.edit_template.text(), ts, frame_index, elapsed)

        self.overlay_item.setPlainText(text)
        self.apply_overlay_style()
        self.place_overlay_text()

    def get_ass_preview_text(self, media_sec: float) -> str:
        if media_sec < self.last_media_sec:
            self.ass_preview_cursor = 0
        self.last_media_sec = media_sec

        n = len(self.ass_preview_events)
        i = self.ass_preview_cursor
        while i < n and media_sec >= self.ass_preview_events[i][1]:
            i += 1
        self.ass_preview_cursor = i

        if i < n:
            start, end, text = self.ass_preview_events[i]
            if start <= media_sec < end:
                return text
        return ""

    def apply_overlay_style(self) -> None:
        font = QFont("Arial")
        font.setPixelSize(self.spin_font.value())
        self.overlay_item.setFont(font)
        self.overlay_item.setDefaultTextColor(QColor(normalize_hex_color(self.edit_color.text().strip())))

    def place_overlay_text(self) -> None:
        rect = self.overlay_item.boundingRect()
        w = self.scene.sceneRect().width()
        h = self.scene.sceneRect().height()

        mx = self.spin_margin_x.value()
        my = self.spin_margin_y.value()
        anchor = self.combo_anchor.currentText()

        if anchor == "free":
            x = mx
            y = my
        else:
            x = mx
            y = my
            if "center" in anchor:
                x = (w - rect.width()) / 2
            if "right" in anchor:
                x = max(0.0, w - rect.width() - mx)
            if anchor.startswith("middle"):
                y = (h - rect.height()) / 2
            if anchor.startswith("bottom"):
                y = max(0.0, h - rect.height() - my)

        self.suppress_overlay_move_event = True
        self.overlay_item.setPos(x, y)
        self.suppress_overlay_move_event = False

    def on_process_finished(self, exit_code: int, _status) -> None:
        self.btn_export.setEnabled(True)
        self.btn_export_20s.setEnabled(True)
        if exit_code == 0:
            self.log.appendPlainText("渲染完成。")
        else:
            self.log.appendPlainText(f"渲染失败，退出码: {exit_code}")

    def append_process_output(self) -> None:
        stdout = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        stderr = bytes(self.process.readAllStandardError()).decode(errors="replace")
        text = (stdout + stderr).strip()
        if text:
            self.log.appendPlainText(text)

    def build_time_config(self) -> TimeConfig:
        interval = float(self.spin_interval.value())
        if self.chk_normal_speed.isChecked():
            interval = 1.0 / max(0.0001, float(self.video_fps))
        return TimeConfig(
            start_time=self.edit_start.dateTime().toPython(),
            capture_interval_sec=interval,
            updates_per_second=int(self.spin_ups.value()),
        )

    def build_style(self) -> OsdStyle:
        return OsdStyle(
            font_name="Arial",
            font_size=int(self.spin_font.value()),
            color_hex=normalize_hex_color(self.edit_color.text().strip()),
            outline=2,
            shadow=1,
            margin_x=int(self.spin_margin_x.value()),
            margin_y=int(self.spin_margin_y.value()),
            anchor=self.combo_anchor.currentText(),
        )


def probe_video(video_path: Path, ffprobe_bin: str) -> tuple[float, float, int, int, str]:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate,r_frame_rate,width,height,codec_name:format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(cp.stdout)

    duration = float(data.get("format", {}).get("duration", 0.0))

    fps = 30.0
    width = 1920
    height = 1080

    codec = "unknown"

    streams = data.get("streams", [])
    if streams:
        s0 = streams[0]
        rate = s0.get("avg_frame_rate") or s0.get("r_frame_rate") or "0/1"
        fps = parse_fps(rate)
        width = int(s0.get("width") or width)
        height = int(s0.get("height") or height)
        codec = str(s0.get("codec_name") or codec)

    return duration, fps, width, height, codec


def parse_fps(expr: str) -> float:
    m = re.match(r"^(\d+)/(\d+)$", expr)
    if not m:
        try:
            return float(expr)
        except Exception:
            return 30.0
    num = float(m.group(1))
    den = float(m.group(2))
    if den == 0:
        return 30.0
    return num / den


def parse_ass_events(ass_path: Path) -> list[tuple[float, float, str]]:
    events: list[tuple[float, float, str]] = []
    for line in ass_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        start = ass_time_to_sec(parts[1].strip())
        end = ass_time_to_sec(parts[2].strip())
        text = clean_ass_text(parts[9].strip())
        if end > start:
            events.append((start, end, text))
    return events


def ass_time_to_sec(ts: str) -> float:
    m = re.match(r"^(\d+):(\d{2}):(\d{2})\.(\d{2})$", ts)
    if not m:
        return 0.0
    h = int(m.group(1))
    mm = int(m.group(2))
    s = int(m.group(3))
    cs = int(m.group(4))
    return h * 3600 + mm * 60 + s + cs / 100.0


def clean_ass_text(text: str) -> str:
    text = re.sub(r"\{[^}]*\}", "", text)
    text = text.replace(r"\N", "\n").replace(r"\n", "\n")
    text = text.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
    return text


def normalize_hex_color(color: str) -> str:
    c = color.strip().upper()
    if re.match(r"^#[0-9A-F]{6}$", c):
        return c
    return "#FFFFFF"


def format_hhmmss(seconds: float) -> str:
    total = int(max(0, round(seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def resolve_tool_binary(tool_name: str) -> str:
    exe_name = f"{tool_name}.exe" if sys.platform.startswith("win") else tool_name

    found = shutil.which(exe_name) or shutil.which(tool_name)
    if found:
        return found

    candidates: list[Path] = []

    # PyInstaller onefile extraction directory.
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        mp = Path(meipass)
        candidates.append(mp / exe_name)
        candidates.append(mp / tool_name)
        candidates.append(mp / "ffmpeg" / "bin" / exe_name)
        candidates.append(mp / "tools" / "ffmpeg" / "bin" / exe_name)

    app_dir = Path(sys.executable).resolve().parent
    candidates.append(app_dir / exe_name)
    candidates.append(app_dir / tool_name)
    candidates.append(app_dir / "ffmpeg" / "bin" / exe_name)
    candidates.append(app_dir / "tools" / "ffmpeg" / "bin" / exe_name)

    root_dir = Path(__file__).resolve().parents[2]
    candidates.append(root_dir / exe_name)
    candidates.append(root_dir / "ffmpeg" / "bin" / exe_name)
    candidates.append(root_dir / "tools" / "ffmpeg" / "bin" / exe_name)

    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def run() -> int:
    app = QApplication([])
    icon_path = Path(__file__).resolve().parents[2] / "icon_timeosd.svg"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
    w = MainWindow()
    if icon_path.exists():
        w.setWindowIcon(QIcon(str(icon_path)))
    w.show()
    return app.exec()

