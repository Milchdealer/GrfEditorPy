"""SPR sprite preview (first frame + frame navigator)."""
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox
)
from ..preview.image_preview import ImagePreview
from ...formats.spr import load_all_frames


class SprPreview(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._image_view = ImagePreview()
        layout.addWidget(self._image_view, 1)

        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀")
        self._next_btn = QPushButton("▶")
        self._spin = QSpinBox()
        self._spin.setMinimum(0)
        self._info = QLabel("")
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        nav.addWidget(self._prev_btn)
        nav.addWidget(self._spin)
        nav.addWidget(self._next_btn)
        nav.addWidget(self._info)
        layout.addLayout(nav)

        self._frames = []
        self._prev_btn.clicked.connect(self._prev)
        self._next_btn.clicked.connect(self._next)
        self._spin.valueChanged.connect(self._show_frame)

    def show_bytes(self, data: bytes) -> None:
        self._frames = load_all_frames(data)
        n = len(self._frames)
        self._spin.setMaximum(max(0, n - 1))
        self._spin.setValue(0)
        self._show_frame(0)

    def _show_frame(self, idx: int) -> None:
        if not self._frames:
            self._image_view.clear()
            self._info.setText("No frames")
            return
        idx = max(0, min(idx, len(self._frames) - 1))
        img = self._frames[idx]
        self._image_view.show_image(img)
        self._info.setText(f"Frame {idx + 1}/{len(self._frames)}  {img.width}×{img.height}")

    def _prev(self) -> None:
        self._spin.setValue(max(0, self._spin.value() - 1))

    def _next(self) -> None:
        self._spin.setValue(min(self._spin.maximum(), self._spin.value() + 1))

    def clear(self) -> None:
        self._frames = []
        self._image_view.clear()
        self._info.setText("")
