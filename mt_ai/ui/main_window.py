from __future__ import annotations

import json
from pathlib import Path

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
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from mt_ai.analysis.fidelity import compare_source_and_render
from mt_ai.analysis.scene import SceneAnalyzer
from mt_ai.hardware import detect_hardware
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
        self._build_ui()
        self._build_menu()
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
        center_l.addWidget(self.canvas, 1)
        view_row = QHBoxLayout()
        self.original_btn = QPushButton("Original")
        self.rendered_btn = QPushButton("Rendered")
        self.original_btn.clicked.connect(lambda: self.source_image and self.canvas.set_image(self.source_image))
        self.rendered_btn.clicked.connect(lambda: self.render_image and self.canvas.set_image(self.render_image))
        view_row.addWidget(self.original_btn)
        view_row.addWidget(self.rendered_btn)
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
        self.save_btn = QPushButton("Save Result")
        self.open_btn.clicked.connect(self.choose_image)
        self.paste_btn.clicked.connect(self.paste_image)
        self.suggest_btn.clicked.connect(self.suggest_prompt)
        self.rewrite_btn.clicked.connect(self.rewrite_prompt)
        self.render_btn.clicked.connect(self.render)
        self.save_btn.clicked.connect(self.save_result)
        for b in (self.open_btn, self.paste_btn, self.suggest_btn, self.rewrite_btn, self.render_btn, self.save_btn):
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

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self.render_btn.setEnabled(not busy)
        self.progress.setRange(0, 0 if busy else 1)
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
        source = self.source_image.copy()
        prompt = self._full_prompt()
        quality = self.quality.currentText()
        profile = hw.recommended_profile if hw.recommended_profile in {"quality", "balanced", "low-memory"} else "low-memory"

        def job():
            result = QwenEngine(active).render(
                RenderRequest(source=source, prompt=prompt, quality=quality, memory_profile=profile)
            )
            fidelity = compare_source_and_render(source, result.image)
            return result, fidelity

        worker = FunctionWorker(job)
        worker.signals.result.connect(self._render_done)
        worker.signals.error.connect(self._render_error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self._set_busy(True, "Rendering locally with Qwen Image...")
        self.thread_pool.start(worker)

    def _render_done(self, payload) -> None:
        result, fidelity = payload
        self.render_image = result.image
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
        QMessageBox.critical(self, "Render failed", message)

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
