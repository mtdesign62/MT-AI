from __future__ import annotations

import sys

from mt_ai.version import APP_NAME

DARK_STYLE = """
QWidget { background: #171b22; color: #e7ebf0; font-size: 13px; }
QMainWindow, QDialog { background: #171b22; }
QPushButton { background: #252c36; border: 1px solid #384250; border-radius: 6px; padding: 8px 12px; }
QPushButton:hover { background: #303946; }
QPushButton:disabled { color: #6f7884; }
QPlainTextEdit, QListWidget, QComboBox { background: #11151b; border: 1px solid #343d49; border-radius: 5px; padding: 5px; }
QGroupBox { border: 1px solid #313945; border-radius: 6px; margin-top: 12px; padding-top: 8px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QProgressBar { border: 1px solid #343d49; border-radius: 4px; text-align: center; min-height: 10px; }
QProgressBar::chunk { background: #4e8cff; }
"""


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
        from mt_ai.ui.main_window import MainWindow
    except ImportError as exc:
        print("MT AI GUI requires PySide6. Install requirements/base.txt", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
