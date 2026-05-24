"""Image preview widget with zoom support."""
import io
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPixmap, QWheelEvent
from PySide6.QtWidgets import QScrollArea, QLabel, QWidget, QVBoxLayout, QSizePolicy


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    img_rgba = img.convert("RGBA")
    data = img_rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, img_rgba.width, img_rgba.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class ImagePreview(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setWidget(self._label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pixmap: Optional[QPixmap] = None
        self._scale = 1.0

    def show_image(self, img: Image.Image) -> None:
        self._pixmap = pil_to_qpixmap(img)
        self._scale = 1.0
        self._update()

    def show_bytes(self, data: bytes, ext: str = "") -> None:
        try:
            img = Image.open(io.BytesIO(data))
            self.show_image(img)
        except Exception as e:
            self._label.setText(f"Cannot decode image:\n{e}")

    def clear(self) -> None:
        self._pixmap = None
        self._label.clear()
        self._label.setText("No preview")

    def _update(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            int(self._pixmap.width() * self._scale),
            int(self._pixmap.height() * self._scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            self._scale = max(0.05, min(self._scale * factor, 32.0))
            self._update()
            event.accept()
        else:
            super().wheelEvent(event)
