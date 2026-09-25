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
        self._compare_original: Image.Image | None = None
        self._compare_rendered: Image.Image | None = None
        self._compare_percent = 50
        self._scale = 1.0
        self.setStyleSheet("QScrollArea { background: #11151b; border: 1px solid #2a313d; }")

    def set_image(self, image: Image.Image) -> None:
        self._compare_original = None
        self._compare_rendered = None
        self._image = image.copy()
        self._scale = 1.0
        self._refresh()

    def set_comparison(self, original: Image.Image, rendered: Image.Image, percent: int = 50) -> None:
        self._image = None
        self._compare_original = original.copy()
        self._compare_rendered = rendered.copy()
        self._compare_percent = max(0, min(100, int(percent)))
        self._refresh()

    def set_comparison_percent(self, percent: int) -> None:
        self._compare_percent = max(0, min(100, int(percent)))
        if self._compare_original is not None and self._compare_rendered is not None:
            self._refresh()

    def clear_image(self) -> None:
        self._image = self._compare_original = self._compare_rendered = None
        self.label.setPixmap(QPixmap())
        self.label.setText("Drop a SketchUp / 3ds Max / Blender screenshot here")

    def _display_image(self) -> Image.Image | None:
        if self._compare_original is None or self._compare_rendered is None:
            return self._image
        original = self._compare_original.convert("RGB")
        rendered = self._compare_rendered.convert("RGB")
        if rendered.size != original.size:
            rendered = rendered.resize(original.size, Image.Resampling.LANCZOS)
        # Slider semantics requested by MT AI: left = full render, right = full original.
        cut = round(original.width * self._compare_percent / 100)
        combined = rendered.copy()
        if cut > 0:
            combined.paste(original.crop((0, 0, cut, original.height)), (0, 0))
        return combined

    def _refresh(self) -> None:
        image = self._display_image()
        if image is None:
            return
        pix = pil_to_qpixmap(image)
        viewport = self.viewport().size()
        target = pix.size()
        target.scale(viewport.width() - 24, viewport.height() - 24, Qt.AspectRatioMode.KeepAspectRatio)
        self.label.setPixmap(pix.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.label.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()
