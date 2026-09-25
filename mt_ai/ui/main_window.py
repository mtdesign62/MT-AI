from __future__ import annotations

import json
from pathlib import Path
from threading import Event

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from mt_ai.analysis.fidelity import compare_source_and_render
from mt_ai.analysis.scene import SceneAnalyzer
from mt_ai.hardware import detect_hardware
from mt_ai.i18n import current_language, localize_widget, relocalize_widget, tr
from mt_ai.inference.qwen import QwenEngine
from mt_ai.inference.types import RenderRequest
from mt_ai.models.manager import ModelManager
from mt_ai.projects import ProjectManager
from mt_ai.prompts import MODE_DEFAULTS, ProtectionOptions, RenderIntent, build_prompt, suggest_user_prompt
from mt_ai.version import APP_NAME, APP_SUBTITLE, APP_VERSION

from .canvas import ImageCanvas
from .model_dialog import ModelManagerDialog


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(int, int)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            value = self.fn()
            self.signals.result.emit(value)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class DropWindow(QMainWindow):
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                self.open_image(path)
                break


class MainWindow(DropWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} — {APP_SUBTITLE}")
        self.resize(1500, 920)
        self.manager = ModelManager()
        self.project_manager = ProjectManager()
        self.current_project = None
        self.scene_analyzer = SceneAnalyzer()
        self.thread_pool = QThreadPool.globalInstance()
        self.source_image: Image.Image | None = None
        self.render_image: Image.Image | None = None
        self.source_path: Path | None = None
        self.scene_analysis = None
        self.current_mode = "Interior"
        self.render_cancel_event = Event()
        self.last_render_request: dict | None = None
        self._build_ui()
        self._build_menu()
        self.language = current_language()
        localize_widget(self, self.language)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} — {tr(APP_SUBTITLE, self.language)} · {self.language.upper()}")
        self._refresh_model_status()
        self._refresh_hardware()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(splitter, 1)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.addWidget(QLabel("RENDER"))
        self.mode_list = QListWidget()
        self.mode_list.addItems(["Interior", "Architecture", "Landscape", "Masterplan", "Enhance", "Upscale"])
        self.mode_list.setCurrentRow(0)
        self.mode_list.currentTextChanged.connect(self._mode_changed)
        left_l.addWidget(self.mode_list)
        self.models_btn = QPushButton("Model Manager")
        self.models_btn.clicked.connect(self.open_model_manager)
        left_l.addWidget(self.models_btn)
        left_l.addStretch(1)
        splitter.addWidget(left)

        center = QWidget()
        center_l = QVBoxLayout(center)
        self.canvas = ImageCanvas()
        self.compare_slider = QSlider(Qt.Orientation.Horizontal)
        self.compare_slider.setRange(0, 100)
        self.compare_slider.setValue(50)
        self.compare_slider.setVisible(False)
        self.compare_slider.valueChanged.connect(self.canvas.set_comparison_percent)
        center_l.addWidget(self.compare_slider)
        center_l.addWidget(self.canvas, 1)
        view_row = QHBoxLayout()
        self.original_btn = QPushButton("Original")
        self.rendered_btn = QPushButton("Rendered")
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setCheckable(True)
        self.original_btn.clicked.connect(lambda: self._show_single_image(self.source_image))
        self.rendered_btn.clicked.connect(lambda: self._show_single_image(self.render_image))
        self.compare_btn.toggled.connect(self._toggle_compare)
        view_row.addWidget(self.original_btn)
        view_row.addWidget(self.rendered_btn)
        view_row.addWidget(self.compare_btn)
        view_row.addStretch(1)
        center_l.addLayout(view_row)
        splitter.addWidget(center)

        right = QWidget()
        right_l = QVBoxLayout(right)
        self.model_label = QLabel("Model: ...")
        right_l.addWidget(self.model_label)
        self.hardware_label = QLabel("Hardware: ...")
        self.hardware_label.setWordWrap(True)
        right_l.addWidget(self.hardware_label)
        group = QGroupBox("Scene Analysis")
        gl = QVBoxLayout(group)
        self.analysis_text = QLabel("Load an image to analyze the scene.")
        self.analysis_text.setWordWrap(True)
        gl.addWidget(self.analysis_text)
        self.analyze_btn = QPushButton("Analyze Scene")
        self.analyze_btn.clicked.connect(self.analyze_scene)
        gl.addWidget(self.analyze_btn)
        right_l.addWidget(group)

        right_l.addWidget(QLabel("Mood / context"))
        self.mood = QComboBox()
        self.mood.addItems(["Natural", "Morning", "Afternoon", "Golden hour", "Blue hour", "Night", "Soft cloudy", "Warm luxury", "Neutral studio"])
        right_l.addWidget(self.mood)
        right_l.addWidget(QLabel("Geometry Protection"))
        self.geometry = QSlider(Qt.Orientation.Horizontal)
        self.geometry.setRange(0, 100)
        self.geometry.setValue(90)
        self.geometry_label = QLabel("90 / 100")
        self.geometry.valueChanged.connect(lambda v: self.geometry_label.setText(f"{v} / 100"))
        right_l.addWidget(self.geometry)
        right_l.addWidget(self.geometry_label)

        protect = QGroupBox("Render Protection")
        pl = QVBoxLayout(protect)
        self.protect_checks = {}
        for key, label in [
            ("camera", "Camera"), ("architecture", "Architecture"), ("furniture", "Furniture"),
            ("windows", "Windows"), ("doors", "Doors"), ("ceiling", "Ceiling"),
            ("major_objects", "Major objects"), ("signage", "Text / signage"),
        ]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.protect_checks[key] = cb
            pl.addWidget(cb)
        right_l.addWidget(protect)
        right_l.addWidget(QLabel("Quality"))
        self.quality = QComboBox()
        self.quality.addItems(["Draft", "Standard", "High", "Ultra"])
        self.quality.setCurrentText("Standard")
        right_l.addWidget(self.quality)
        right_l.addWidget(QLabel("Output Resolution"))
        self.resolution = QComboBox()
        self.resolution.addItems([
            "Match source", "HD · 1280×720 (16:9)", "Full HD · 1920×1080 (16:9)",
            "2K · 2560×1440 (16:9)", "4K · 3840×2160 (16:9)",
            "Square · 1024×1024 (1:1)", "Portrait · 1080×1350 (4:5)",
            "Story · 1080×1920 (9:16)", "Custom",
        ])
        right_l.addWidget(self.resolution)
        custom_row = QHBoxLayout()
        self.custom_width = QSpinBox(); self.custom_width.setRange(256, 8192); self.custom_width.setSingleStep(32); self.custom_width.setValue(1920)
        self.custom_height = QSpinBox(); self.custom_height.setRange(256, 8192); self.custom_height.setSingleStep(32); self.custom_height.setValue(1080)
        self.custom_width.setEnabled(False); self.custom_height.setEnabled(False)
        custom_row.addWidget(self.custom_width); custom_row.addWidget(QLabel("×")); custom_row.addWidget(self.custom_height)
        right_l.addLayout(custom_row)
        self.resolution.currentTextChanged.connect(self._resolution_changed)
        right_l.addStretch(1)
        splitter.addWidget(right)
        splitter.setSizes([190, 950, 330])

        prompt_box = QGroupBox("Prompt")
        prompt_l = QVBoxLayout(prompt_box)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Example: warm morning light, premium walnut and brown leather, realistic photography")
        self.prompt.setMaximumHeight(110)
        prompt_l.addWidget(self.prompt)
        buttons = QHBoxLayout()
        self.open_btn = QPushButton("Open Image")
        self.paste_btn = QPushButton("Paste")
        self.suggest_btn = QPushButton("Suggest Prompt")
        self.rewrite_btn = QPushButton("AI Rewrite Prompt")
        self.render_btn = QPushButton("RENDER")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setEnabled(False)
        self.save_btn = QPushButton("Save Result")
        self.open_btn.clicked.connect(self.choose_image)
        self.paste_btn.clicked.connect(self.paste_image)
        self.suggest_btn.clicked.connect(self.suggest_prompt)
        self.rewrite_btn.clicked.connect(self.rewrite_prompt)
        self.render_btn.clicked.connect(self.render)
        self.cancel_btn.clicked.connect(self.cancel_render)
        self.retry_btn.clicked.connect(self.render)
        self.save_btn.clicked.connect(self.save_result)
        for b in (self.open_btn, self.paste_btn, self.suggest_btn, self.rewrite_btn, self.render_btn, self.cancel_btn, self.retry_btn, self.save_btn):
            buttons.addWidget(b)
        prompt_l.addLayout(buttons)
        main.addWidget(prompt_box)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        main.addWidget(self.progress)
        self.setStatusBar(QStatusBar())

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        open_action = QAction("Open Image", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_image)
        paste_action = QAction("Paste Image", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.paste_image)
        save_action = QAction("Save Result", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_result)
        file_menu.addActions([open_action, paste_action, save_action])
        tools = self.menuBar().addMenu("Tools")
        models = QAction("Model Manager", self)
        models.triggered.connect(self.open_model_manager)
        tools.addAction(models)
        language_menu = self.menuBar().addMenu("Language")
        english = QAction("English", self); english.triggered.connect(lambda: self.set_language("en"))
        vietnamese = QAction("Vietnamese", self); vietnamese.triggered.connect(lambda: self.set_language("vi"))
        language_menu.addActions([english, vietnamese])

    def set_language(self, language: str) -> None:
        self.language = "vi" if language == "vi" else "en"
        relocalize_widget(self, self.language)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} — {tr(APP_SUBTITLE, self.language)} · {self.language.upper()}")
        self.statusBar().showMessage("Đã chuyển sang Tiếng Việt" if self.language == "vi" else "Switched to English")

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self.render_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        if not busy:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
        if text:
            self.statusBar().showMessage(text)

    def _refresh_hardware(self) -> None:
        hw = detect_hardware()
        gpu = hw.gpu_name or "No CUDA GPU"
        vram = f"{hw.vram_total_mb} MB VRAM" if hw.vram_total_mb else "VRAM unavailable"
        self.hardware_label.setText(f"{gpu}\n{vram} · profile {hw.recommended_profile}")

    def _refresh_model_status(self) -> None:
        active = self.manager.active()
        self.model_label.setText(
            f"Model: {active.repo_id} v{active.version}\n{active.revision[:12]}"
            if active else "Model: not installed / not activated"
        )

    def _show_single_image(self, image: Image.Image | None) -> None:
        self.compare_btn.setChecked(False)
        if image is not None:
            self.canvas.set_image(image)

    def _toggle_compare(self, enabled: bool) -> None:
        available = self.source_image is not None and self.render_image is not None
        enabled = enabled and available
        self.compare_slider.setVisible(enabled)
        if enabled:
            self.canvas.set_comparison(self.source_image, self.render_image, self.compare_slider.value())
        elif self.render_image is not None:
            self.canvas.set_image(self.render_image)

    def _resolution_changed(self, value: str) -> None:
        custom = value == "Custom"
        self.custom_width.setEnabled(custom)
        self.custom_height.setEnabled(custom)

    def _output_dimensions(self) -> tuple[int, int] | None:
        value = self.resolution.currentText()
        if value == "Match source":
            return self.source_image.size if self.source_image is not None else None
        if value == "Custom":
            return self.custom_width.value(), self.custom_height.value()
        presets = {
            "HD · 1280×720 (16:9)": (1280, 720), "Full HD · 1920×1080 (16:9)": (1920, 1080),
            "2K · 2560×1440 (16:9)": (2560, 1440), "4K · 3840×2160 (16:9)": (3840, 2160),
            "Square · 1024×1024 (1:1)": (1024, 1024), "Portrait · 1080×1350 (4:5)": (1080, 1350),
            "Story · 1080×1920 (9:16)": (1080, 1920),
        }
        return presets.get(value)

    def _mode_changed(self, mode: str) -> None:
        self.current_mode = mode
        self.geometry.setValue(MODE_DEFAULTS.get(mode, 90))

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open 3D viewport image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.open_image(Path(path))

    def open_image(self, path: Path) -> None:
        try:
            image = Image.open(path).convert("RGB")
        except Exception as exc:
            QMessageBox.critical(self, "Image error", str(exc))
            return
        self.source_path = path
        self.source_image = image
        try:
            self.current_project = self.project_manager.create(path.stem, path)
        except Exception:
            self.current_project = None
        self.render_image = None
        self.canvas.set_image(image)
        self.statusBar().showMessage(str(path))
        self.analyze_scene()

    def paste_image(self) -> None:
        clipboard = QApplication.clipboard()
        qimg = clipboard.image()
        if qimg.isNull():
            QMessageBox.information(self, "Paste", "Clipboard does not contain an image.")
            return
        qimg = qimg.convertToFormat(qimg.Format.Format_RGBA8888)
        ptr = qimg.bits()
        data = bytes(ptr[: qimg.sizeInBytes()])
        self.source_image = Image.frombytes("RGBA", (qimg.width(), qimg.height()), data).convert("RGB")
        self.source_path = None
        self.current_project = None
        self.render_image = None
        self.canvas.set_image(self.source_image)
        self.analyze_scene()

    def analyze_scene(self) -> None:
        if self.source_image is None:
            return
        self.scene_analysis = self.scene_analyzer.analyze(self.source_image, self.current_mode)
        a = self.scene_analysis
        self.analysis_text.setText(
            f"Mode: {a.mode_hint}\nSource: {a.width}×{a.height}\nLighting: {a.lighting_hint}\n"
            f"Geometry: {a.geometry_complexity}\nEdge density: {a.edge_density:.3f}\n"
            f"Analyzer confidence: {a.confidence:.0%} (V1 heuristic)"
        )

    def suggest_prompt(self) -> None:
        self.prompt.setPlainText(suggest_user_prompt(self.current_mode, self.mood.currentText()))

    def rewrite_prompt(self) -> None:
        if self.source_image is None:
            QMessageBox.information(self, "AI Rewrite", "Open or paste an image first.")
            return
        rewriter_model = self.manager.active("qwen-image-prompt-rewriter")
        if rewriter_model is None:
            QMessageBox.information(
                self,
                "Prompt Rewriter",
                "The optional Qwen PE-I2I prompt rewriter is not installed. Open Model Manager to install it.",
            )
            return
        source = self.source_image.copy()
        user_prompt = self.prompt.toPlainText() or suggest_user_prompt(self.current_mode, self.mood.currentText())
        def job():
            from mt_ai.prompt_rewriter import QwenPEI2IRewriter
            return QwenPEI2IRewriter(rewriter_model).rewrite(source, user_prompt)
        worker = FunctionWorker(job)
        worker.signals.result.connect(lambda result: self.prompt.setPlainText(result.rewritten_prompt))
        worker.signals.error.connect(self._render_error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Prompt rewrite complete"))
        self._set_busy(True, "Analyzing image and rewriting prompt with Qwen PE-I2I...")
        self.thread_pool.start(worker)

    def _protections(self) -> ProtectionOptions:
        return ProtectionOptions(**{key: cb.isChecked() for key, cb in self.protect_checks.items()})

    def _full_prompt(self) -> str:
        return build_prompt(
            RenderIntent(
                mode=self.current_mode,
                user_prompt=self.prompt.toPlainText(),
                geometry_strength=self.geometry.value(),
                mood=self.mood.currentText(),
                protections=self._protections(),
                scene_summary=self.scene_analysis.summary() if self.scene_analysis else "",
            )
        )

    def render(self) -> None:
        if self.source_image is None:
            QMessageBox.information(self, "Render", "Open or paste a source image first.")
            return
        if self.current_mode == "Upscale":
            from mt_ai.upscale import LanczosUpscaleBackend
            self.render_image = LanczosUpscaleBackend().upscale(self.source_image, 2)
            self.canvas.set_image(self.render_image)
            return
        active = self.manager.active()
        if active is None:
            QMessageBox.information(self, "Model required", "Install and activate Qwen Image from Model Manager first.")
            self.open_model_manager()
            return
        hw = detect_hardware()
        if not hw.cuda_available:
            QMessageBox.warning(self, "CUDA required", "No NVIDIA CUDA GPU is available. Local Qwen rendering cannot start on this machine.")
            return
        if hw.recommended_profile == "unsupported":
            QMessageBox.warning(self, "VRAM required", "MT AI requires an NVIDIA CUDA GPU with at least 12 GB VRAM for local Qwen Image 2.1 rendering.")
            return
        source = self.source_image.copy()
        prompt = self._full_prompt()
        self.render_cancel_event.clear()
        quality = self.quality.currentText()
        steps = {"Draft": 4, "Standard": 8, "High": 12, "Ultra": 20}.get(quality, 8)
        dimensions = self._output_dimensions()
        self.last_render_request = {"quality": quality, "steps": steps, "profile": hw.recommended_profile, "dimensions": dimensions}
        profile = hw.recommended_profile if hw.recommended_profile in {"quality", "balanced", "low-memory", "low-memory-12gb"} else "low-memory-12gb"

        def job():
            result = QwenEngine(active).render(
                RenderRequest(source=source, prompt=prompt, quality=quality, steps=steps, memory_profile=profile,
                              width=dimensions[0] if dimensions else None, height=dimensions[1] if dimensions else None),
                cancel_check=self.render_cancel_event.is_set,
                progress=lambda done, total: worker.signals.progress.emit(done, total),
            )
            fidelity = compare_source_and_render(source, result.image)
            return result, fidelity

        worker = FunctionWorker(job)
        worker.signals.progress.connect(self._render_progress)
        worker.signals.result.connect(self._render_done)
        worker.signals.error.connect(self._render_error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self._set_busy(True, f"Rendering locally with Qwen Image · {steps} steps...")
        self.progress.setRange(0, steps)
        self.progress.setValue(0)
        self.thread_pool.start(worker)

    def cancel_render(self) -> None:
        self.render_cancel_event.set()
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage("Cancelling render at the next diffusion step...")

    def _render_progress(self, done: int, total: int) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(done)
        self.statusBar().showMessage(f"Rendering · step {done}/{total}")

    def _render_done(self, payload) -> None:
        result, fidelity = payload
        self.render_image = result.image
        self.compare_btn.setEnabled(True)
        self.retry_btn.setEnabled(True)
        self.canvas.set_image(self.render_image)
        if self.current_project is not None:
            try:
                metadata = result.serializable_metadata()
                metadata["fidelity"] = {
                    "overall_score": fidelity.overall_score,
                    "edge_score": fidelity.edge_score,
                    "orientation_score": fidelity.orientation_score,
                }
                self.project_manager.save_render(self.current_project, self.render_image, metadata)
            except Exception as exc:
                self.statusBar().showMessage(f"Render complete; history save failed: {exc}")
        self.statusBar().showMessage(
            f"Done in {result.duration_seconds:.1f}s · Structural Fidelity {fidelity.overall_score:.1%}"
        )

    def _render_error(self, message: str) -> None:
        self.retry_btn.setEnabled(self.source_image is not None)
        if "cancelled" in message.lower():
            self.statusBar().showMessage("Render cancelled")
            return
        friendly = message
        if "out of memory" in message.lower():
            friendly = "GPU memory is full. MT AI will keep the source image; retry with Draft/Standard quality or Low Memory mode.\n\n" + message
        QMessageBox.critical(self, "Render failed", friendly)

    def save_result(self) -> None:
        if self.render_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save render", "mt_ai_render.png", "PNG (*.png);;JPEG (*.jpg)")
        if path:
            self.render_image.save(path)

    def open_model_manager(self) -> None:
        dlg = ModelManagerDialog(self.manager, self)
        dlg.model_changed.connect(self._refresh_model_status)
        dlg.exec()
