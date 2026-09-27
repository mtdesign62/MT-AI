from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class DiagnosticsDialog(QDialog):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("MT AI — Diagnostics")
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(text)
        layout.addWidget(self.output, 1)

        buttons = QHBoxLayout()
        copy_btn = QPushButton("Copy Diagnostics")
        close_btn = QPushButton("Close")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.output.toPlainText())
        )
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(copy_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
