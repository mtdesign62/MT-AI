from __future__ import annotations

import sys
import traceback
from pathlib import Path

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

SELF_TEST_REPORT = Path("mt_ai_ai_self_test_report.txt")


def ai_runtime_self_test() -> int:
    """Packaging smoke test: verify the frozen app contains the local Qwen runtime."""
    try:
        import accelerate  # noqa: F401
        import diffusers
        import safetensors  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401

        if not hasattr(diffusers, "QwenImage21Pipeline"):
            SELF_TEST_REPORT.write_text(
                "QwenImage21Pipeline is missing from packaged Diffusers.\n",
                encoding="utf-8",
            )
            return 4

        SELF_TEST_REPORT.write_text(
            "PASS\n"
            f"diffusers={getattr(diffusers, '__version__', 'unknown')}\n"
            f"transformers={getattr(transformers, '__version__', 'unknown')}\n"
            f"torch={getattr(torch, '__version__', 'unknown')}\n",
            encoding="utf-8",
        )
    except Exception:
        SELF_TEST_REPORT.write_text(traceback.format_exc(), encoding="utf-8")
        return 3
    return 0


def main() -> int:
    if "--self-test-ai" in sys.argv:
        return ai_runtime_self_test()

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
