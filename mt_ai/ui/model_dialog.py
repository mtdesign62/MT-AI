from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QProgressBar, QVBoxLayout, QPlainTextEdit,
)

from mt_ai.models.manager import ModelManager
from mt_ai.i18n import current_language, localize_widget
from mt_ai.models.registry import DEFAULT_IMAGE_MODEL, DEFAULT_PROMPT_REWRITER
from mt_ai.models.schemas import ModelCandidate


class ModelTask(QThread):
    status = Signal(str)
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn

    def run(self) -> None:
        try:
            result = self.fn(self.status.emit)
            self.result_ready.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ModelManagerDialog(QDialog):
    model_changed = Signal()

    def __init__(self, manager: ModelManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("MT AI — Model Manager")
        self.resize(760, 520)
        self.candidates: list[ModelCandidate] = []
        self.worker: ModelTask | None = None
        layout = QVBoxLayout(self)
        self.active_label = QLabel()
        layout.addWidget(self.active_label)
        layout.addWidget(QLabel("Installed Qwen Image models"))
        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list, 1)
        row = QHBoxLayout()
        self.import_btn = QPushButton("Import Existing Model")
        self.install_btn = QPushButton("Install Qwen Image 2.1")
        self.guide_btn = QPushButton("PowerShell Download Guide")
        self.rewriter_btn = QPushButton("Install Prompt Rewriter (optional)")
        self.activate_btn = QPushButton("Activate selected")
        self.rollback_btn = QPushButton("Rollback")
        row.addWidget(self.import_btn); row.addWidget(self.install_btn); row.addWidget(self.guide_btn); row.addWidget(self.rewriter_btn); row.addWidget(self.activate_btn); row.addWidget(self.rollback_btn)
        layout.addLayout(row)
        layout.addWidget(QLabel("Available official Qwen updates"))
        self.updates_list = QListWidget()
        layout.addWidget(self.updates_list, 1)
        row2 = QHBoxLayout()
        self.check_btn = QPushButton("Check updates")
        self.install_update_btn = QPushButton("Install selected update")
        row2.addWidget(self.check_btn); row2.addWidget(self.install_update_btn)
        layout.addLayout(row2)
        self.status_label = QLabel("Ready")
        self.progress = QProgressBar(); self.progress.setRange(0, 1)
        layout.addWidget(self.status_label); layout.addWidget(self.progress)
        self.import_btn.clicked.connect(self.import_existing)
        self.install_btn.clicked.connect(self.install_default)
        self.guide_btn.clicked.connect(self.show_download_guide)
        self.rewriter_btn.clicked.connect(self.install_rewriter)
        self.activate_btn.clicked.connect(self.activate_selected)
        self.rollback_btn.clicked.connect(self.rollback)
        self.check_btn.clicked.connect(self.check_updates)
        self.install_update_btn.clicked.connect(self.install_selected_update)
        self.refresh()
        localize_widget(self, current_language())

    def _busy(self, value: bool) -> None:
        for button in (self.import_btn, self.install_btn, self.guide_btn, self.rewriter_btn, self.activate_btn, self.rollback_btn, self.check_btn, self.install_update_btn):
            button.setEnabled(not value)
        self.progress.setRange(0, 0 if value else 1)

    def _run(self, fn, done) -> None:
        self._busy(True)
        self.worker = ModelTask(fn)
        self.worker.status.connect(self.status_label.setText)
        self.worker.result_ready.connect(lambda result: self._finish(result, done))
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _finish(self, result, done) -> None:
        self._busy(False); done(result); self.refresh()

    def _fail(self, message: str) -> None:
        self._busy(False); self.status_label.setText(message); QMessageBox.critical(self, "Model operation failed", message)

    def refresh(self) -> None:
        active = self.manager.active()
        self.active_label.setText(f"Active: {active.repo_id}  {active.version}  {active.revision[:12]}" if active else "Active: none")
        self.installed_list.clear()
        for model in self.manager.list_installed():
            self.installed_list.addItem(f"{model.repo_id} | v{model.version} | {model.revision[:12]}")

    def import_existing(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select existing Qwen Image 2.1 folder")
        if not folder:
            return
        try:
            model = self.manager.import_existing(folder)
            self.manager.activate(model)
            self.status_label.setText("Existing model imported and activated")
            self.model_changed.emit()
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Import model failed", str(exc))

    def show_download_guide(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Qwen Image 2.1 — PowerShell Download Guide")
        dialog.resize(760, 430)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            "Nếu chưa có model, mở Windows PowerShell và chạy lần lượt các lệnh dưới đây. "
            "Bạn có thể đổi D:\\MT-AI\\Models\\Qwen-Image-2.1 thành thư mục khác nếu muốn."
        ))
        commands = QPlainTextEdit()
        commands.setReadOnly(True)
        commands.setPlainText(
            'py -m pip install -U "huggingface_hub[cli]"\n\n'
            'hf download Qwen/Qwen-Image-2.1 --local-dir "D:\\MT-AI\\Models\\Qwen-Image-2.1"'
        )
        layout.addWidget(commands)
        layout.addWidget(QLabel(
            "Tải xong: bấm “Thêm model có sẵn / Import Existing Model”, chọn đúng thư mục "
            "Qwen-Image-2.1 rồi MT AI sẽ kiểm tra và kích hoạt model."
        ))
        close_btn = QPushButton("Đóng / Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def install_default(self) -> None:
        def fn(status): return self.manager.install_spec(DEFAULT_IMAGE_MODEL, progress=status)
        def done(model):
            self.manager.activate(model); self.status_label.setText("Installed and activated Qwen Image 2.1"); self.model_changed.emit()
        self._run(fn, done)

    def install_rewriter(self) -> None:
        def fn(status): return self.manager.install_spec(DEFAULT_PROMPT_REWRITER, progress=status)
        def done(model):
            self.manager.activate(model); self.status_label.setText("Prompt rewriter installed and activated"); self.model_changed.emit()
        self._run(fn, done)

    def check_updates(self) -> None:
        def fn(status):
            status("Checking official Qwen releases..."); return self.manager.check_updates()
        def done(items):
            self.candidates = list(items); self.updates_list.clear()
            for item in self.candidates:
                self.updates_list.addItem(f"{item.repo_id} | {item.update_kind} | {item.compatibility} | {item.revision[:12]}")
            self.status_label.setText(f"Found {len(self.candidates)} update candidate(s)")
        self._run(fn, done)

    def install_selected_update(self) -> None:
        row = self.updates_list.currentRow()
        if row < 0 or row >= len(self.candidates):
            QMessageBox.information(self, "Select model", "Select an update candidate first."); return
        candidate = self.candidates[row]
        if candidate.compatibility == "dependency-update-required":
            answer = QMessageBox.question(self, "Diffusers update required", "This model is not supported by the currently installed Diffusers build. Download it anyway?")
            if answer != QMessageBox.StandardButton.Yes: return
        def fn(status): return self.manager.install_candidate(candidate, progress=status)
        def done(model):
            if candidate.compatibility == "compatible":
                self.manager.activate(model); self.model_changed.emit(); self.status_label.setText("Update installed and activated")
            else:
                self.status_label.setText("Update installed but not activated; update dependencies first")
        self._run(fn, done)

    def activate_selected(self) -> None:
        row = self.installed_list.currentRow(); items = self.manager.list_installed()
        if row < 0 or row >= len(items): return
        self.manager.activate(items[row]); self.model_changed.emit(); self.refresh()

    def rollback(self) -> None:
        try:
            self.manager.rollback(); self.model_changed.emit(); self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Rollback", str(exc))
