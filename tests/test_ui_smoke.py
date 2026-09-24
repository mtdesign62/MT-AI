import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mt_ai.ui.main_window import MainWindow


def test_main_window_constructs_and_closes():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle().startswith("MT AI")
    assert window.mode_list.count() == 6
    assert window.render_btn.text() == "RENDER"
    window.close()
    app.processEvents()
