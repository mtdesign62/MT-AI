from __future__ import annotations

from PIL import Image

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    rgb = image.convert("RGBA")
    data = rgb.tobytes("raw", "RGBA")
    qimg = QImage(data, rgb.width, rgb.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class ImageCanvas(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel("Drop a SketchUp / 3ds Max / Blender screenshot here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(640, 480)
        self.setWidget(self.label)
        self.setWidgetResizable(True)
        self._image: Image.Image | None = None
        self._scale = 1.0
        self.setStyleSheet("QScrollArea { background: #11151b; border: 1px solid #2a313d; }")

    def set_image(self, image: Image.Image) -> None:
        self._image = image.copy()
        self._scale = 1.0
        self._refresh()

    def clear_image(self) -> None:
        self._image = None
        self.label.setPixmap(QPixmap())
        self.label.setText("Drop a SketchUp / 3ds Max / Blender screenshot here")

    def _refresh(self) -> None:
        if self._image is None:
            return
        pix = pil_to_qpixmap(self._image)
        viewport = self.viewport().size()
        target = pix.size()
        target.scale(viewport.width() - 24, viewport.height() - 24, Qt.AspectRatioMode.KeepAspectRatio)
        self.label.setPixmap(pix.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.label.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()
