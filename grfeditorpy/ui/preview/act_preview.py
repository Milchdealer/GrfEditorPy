"""ACT animation preview widget."""
from __future__ import annotations
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSizePolicy
)

from ...formats.act import Act, ActAction
from ..preview.image_preview import pil_to_qpixmap

# Standard RO action names indexed by action slot
_ACTION_NAMES = [
    "Stand", "Walk", "Sit", "Look", "Weapon",
    "Hit", "Freeze1", "Dead", "Freeze2",
    "Attack1", "Attack2", "Attack3",
]

_CANVAS_MIN = 128   # minimum canvas size in pixels


def _action_name(idx: int) -> str:
    if idx < len(_ACTION_NAMES):
        return f"{idx}: {_ACTION_NAMES[idx]}"
    return f"{idx}: Action {idx}"


def _render_frame(act: Act, action_idx: int, frame_idx: int,
                  spr_frames: list[Image.Image],
                  n_indexed: int,
                  canvas_w: int, canvas_h: int) -> Image.Image:
    """Composite all layers of a single ACT frame onto an RGBA canvas."""
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    cx = canvas_w // 2
    cy = canvas_h // 2

    action = act.actions[action_idx]
    if frame_idx >= len(action.frames):
        return canvas

    for layer in action.frames[frame_idx].layers:
        if layer.sprite_index < 0 or not spr_frames:
            continue

        # Absolute index into spr_frames list
        if layer.sprite_type == 0:  # Indexed8
            abs_idx = layer.sprite_index
        else:                        # Bgra32
            abs_idx = n_indexed + layer.sprite_index

        if abs_idx < 0 or abs_idx >= len(spr_frames):
            continue

        sprite = spr_frames[abs_idx].copy().convert("RGBA")

        # Apply color tint (multiply)
        cr, cg, cb, ca = layer.color
        if (cr, cg, cb, ca) != (255, 255, 255, 255):
            import PIL.ImageEnhance
            r, g, b, a_ch = sprite.split()
            r = r.point(lambda p: p * cr // 255)
            g = g.point(lambda p: p * cg // 255)
            b = b.point(lambda p: p * cb // 255)
            sprite = Image.merge("RGBA", (r, g, b, a_ch))

        # Scale
        sx = abs(layer.scale_x) if layer.scale_x != 0 else 1.0
        sy = abs(layer.scale_y) if layer.scale_y != 0 else 1.0
        if sx != 1.0 or sy != 1.0:
            new_w = max(1, int(sprite.width * sx))
            new_h = max(1, int(sprite.height * sy))
            sprite = sprite.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Mirror
        if layer.mirror:
            sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        # Rotation (nearest 90° snap for performance; most sprites use 0°)
        rot = layer.rotation % 360
        if rot != 0:
            sprite = sprite.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)

        # Paste at center + offset
        x = cx + layer.offset_x - sprite.width // 2
        y = cy + layer.offset_y - sprite.height // 2

        # Clip to canvas
        src_x0 = max(0, -x)
        src_y0 = max(0, -y)
        dst_x = max(0, x)
        dst_y = max(0, y)
        paste_w = min(sprite.width - src_x0, canvas_w - dst_x)
        paste_h = min(sprite.height - src_y0, canvas_h - dst_y)
        if paste_w <= 0 or paste_h <= 0:
            continue

        sprite_crop = sprite.crop((src_x0, src_y0, src_x0 + paste_w, src_y0 + paste_h))
        canvas_region = canvas.crop((dst_x, dst_y, dst_x + paste_w, dst_y + paste_h))
        canvas.paste(Image.alpha_composite(canvas_region, sprite_crop), (dst_x, dst_y))

    return canvas


def _compute_canvas_size(act: Act, spr_frames: list[Image.Image], n_indexed: int) -> tuple[int, int]:
    """Compute a fixed canvas size that fits all frames of all actions."""
    max_extent = _CANVAS_MIN
    for action in act.actions:
        for frame in action.frames:
            for layer in frame.layers:
                if layer.sprite_index < 0:
                    continue
                abs_idx = layer.sprite_index if layer.sprite_type == 0 else n_indexed + layer.sprite_index
                if abs_idx < 0 or abs_idx >= len(spr_frames):
                    continue
                img = spr_frames[abs_idx]
                sx = abs(layer.scale_x) if layer.scale_x != 0 else 1.0
                sy = abs(layer.scale_y) if layer.scale_y != 0 else 1.0
                half_w = int(img.width * sx) // 2 + abs(layer.offset_x)
                half_h = int(img.height * sy) // 2 + abs(layer.offset_y)
                max_extent = max(max_extent, half_w * 2, half_h * 2)
    size = max(_CANVAS_MIN, max_extent + 20)
    return size, size


class ActPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._act: Optional[Act] = None
        self._spr_frames: list[Image.Image] = []
        self._n_indexed = 0
        self._canvas_w = _CANVAS_MIN
        self._canvas_h = _CANVAS_MIN
        self._current_action = 0
        self._current_frame = 0
        self._playing = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top controls
        ctrl = QHBoxLayout()
        self._action_combo = QComboBox()
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setCheckable(True)
        self._play_btn.toggled.connect(self._on_play_toggled)
        self._play_btn.setMaximumWidth(80)
        ctrl.addWidget(QLabel("Action:"))
        ctrl.addWidget(self._action_combo, 1)
        ctrl.addWidget(self._play_btn)
        layout.addLayout(ctrl)

        # Frame display
        self._frame_label = QLabel()
        self._frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._frame_label.setMinimumSize(128, 128)
        layout.addWidget(self._frame_label, 1)

        # Status line
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

    def load(self, act: Act, spr_frames: list[Image.Image], n_indexed: int) -> None:
        self._timer.stop()
        self._play_btn.setChecked(False)
        self._act = act
        self._spr_frames = spr_frames
        self._n_indexed = n_indexed
        self._current_frame = 0
        self._current_action = 0

        self._canvas_w, self._canvas_h = _compute_canvas_size(act, spr_frames, n_indexed)

        self._action_combo.blockSignals(True)
        self._action_combo.clear()
        for i in range(len(act.actions)):
            self._action_combo.addItem(_action_name(i))
        self._action_combo.blockSignals(False)
        self._action_combo.setCurrentIndex(0)

        self._render_current()

    def clear(self) -> None:
        self._timer.stop()
        self._play_btn.setChecked(False)
        self._act = None
        self._spr_frames = []
        self._action_combo.clear()
        self._frame_label.clear()
        self._status_label.setText("")

    def _on_action_changed(self, idx: int) -> None:
        self._current_action = idx
        self._current_frame = 0
        self._render_current()
        if self._playing:
            self._restart_timer()

    def _on_play_toggled(self, playing: bool) -> None:
        self._playing = playing
        if playing:
            self._play_btn.setText("■ Stop")
            self._restart_timer()
        else:
            self._play_btn.setText("▶ Play")
            self._timer.stop()

    def _restart_timer(self) -> None:
        if self._act is None or not self._act.actions:
            return
        action = self._act.actions[self._current_action]
        interval_ms = max(33, int(action.animation_speed * 25))
        self._timer.start(interval_ms)

    def _advance_frame(self) -> None:
        if self._act is None:
            return
        action = self._act.actions[self._current_action]
        n = len(action.frames)
        if n == 0:
            return
        self._current_frame = (self._current_frame + 1) % n
        self._render_current()

    def _render_current(self) -> None:
        if self._act is None:
            return
        action = self._act.actions[self._current_action]
        n_frames = len(action.frames)
        if n_frames == 0:
            self._frame_label.setText("No frames")
            return

        frame_idx = min(self._current_frame, n_frames - 1)
        img = _render_frame(
            self._act, self._current_action, frame_idx,
            self._spr_frames, self._n_indexed,
            self._canvas_w, self._canvas_h
        )
        pixmap = pil_to_qpixmap(img)

        # Scale to fit the label while keeping aspect ratio
        label_size = self._frame_label.size()
        if label_size.width() > 10 and label_size.height() > 10:
            pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._frame_label.setPixmap(pixmap)
        self._status_label.setText(
            f"Frame {frame_idx + 1}/{n_frames}  "
            f"{img.width}×{img.height}  "
            f"Speed: {action.animation_speed:.1f}"
        )
