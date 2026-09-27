import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from mt_ai.i18n import tr
from mt_ai.ui.main_window import MainWindow


def test_main_window_constructs_and_closes():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle().startswith("MT AI")
    assert window.mode_list.count() == 6
    assert window.render_btn.text() == tr("RENDER")
    window.close()
    app.processEvents()



def test_canvas_click_opens_image_picker(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    calls = []

    def fake_get_open_file_name(*args, **kwargs):
        calls.append((args, kwargs))
        return "", ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)
    QTest.mouseClick(window.canvas.label, Qt.MouseButton.LeftButton)
    app.processEvents()

    assert len(calls) == 1
    window.close()
    app.processEvents()


def test_empty_canvas_click_requests_image():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    requested = []
    window.canvas.image_requested.connect(lambda: requested.append(True))
    window.canvas.show()
    app.processEvents()
    QTest.mouseClick(window.canvas.label, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert requested == [True]
    window.close()
    app.processEvents()
