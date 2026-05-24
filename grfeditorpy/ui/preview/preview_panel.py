"""Right panel: routes selected entry to the correct preview widget."""
from typing import Optional
from PySide6.QtWidgets import QStackedWidget, QLabel, QWidget

from .image_preview import ImagePreview
from .text_preview import TextPreview
from .hex_preview import HexPreview
from .spr_preview import SprPreview
from .act_preview import ActPreview
from ...services.preview_service import get_preview_type
from ...formats.pal import load_palette_swatch
from ...formats.spr import load_all_frames
from ...formats.act import parse as parse_act


class PreviewPanel(QStackedWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._empty = QLabel("Select a file to preview")
        self._image = ImagePreview()
        self._text = TextPreview()
        self._hex = HexPreview()
        self._spr = SprPreview()
        self._act = ActPreview()

        self._idx_empty = self.addWidget(self._empty)
        self._idx_image = self.addWidget(self._image)
        self._idx_text = self.addWidget(self._text)
        self._idx_hex = self.addWidget(self._hex)
        self._idx_spr = self.addWidget(self._spr)
        self._idx_act = self.addWidget(self._act)

        self.setCurrentIndex(self._idx_empty)

    def show_entry_data(self, data: bytes, extension: str) -> None:
        kind = get_preview_type(extension)
        try:
            if kind == "image":
                self._image.show_bytes(data, extension)
                self.setCurrentIndex(self._idx_image)
            elif kind == "text":
                self._text.show_bytes(data)
                self.setCurrentIndex(self._idx_text)
            elif kind == "spr":
                self._spr.show_bytes(data)
                self.setCurrentIndex(self._idx_spr)
            elif kind == "pal":
                img = load_palette_swatch(data)
                self._image.show_image(img)
                self.setCurrentIndex(self._idx_image)
            else:
                self._hex.show_bytes(data)
                self.setCurrentIndex(self._idx_hex)
        except Exception as e:
            self._hex.show_bytes(data)
            self._hex.setPlainText(f"Preview failed: {e}\n\n" + self._hex.toPlainText())
            self.setCurrentIndex(self._idx_hex)

    def show_lub_data(self, data: bytes) -> None:
        from ...formats.lub import is_binary, decompile
        try:
            if is_binary(data):
                self._text.show_text(decompile(data))
            else:
                self._text.show_bytes(data)
            self.setCurrentIndex(self._idx_text)
        except Exception as e:
            self._hex.show_bytes(data)
            self._hex.setPlainText(f"LUB preview failed: {e}\n\n" + self._hex.toPlainText())
            self.setCurrentIndex(self._idx_hex)

    def show_act_data(self, act_data: bytes, spr_data: Optional[bytes]) -> None:
        try:
            act = parse_act(act_data)
            spr_frames = load_all_frames(spr_data) if spr_data else []
            # Count indexed8 frames so sprite_type=1 offsets correctly
            n_indexed = 0
            if spr_data and len(spr_data) >= 8 and spr_data[0:2] == b"SP":
                import struct
                minor = spr_data[2]; major = spr_data[3]
                version = major + minor * 0.1
                if version >= 2.0:
                    n_indexed = struct.unpack_from("<H", spr_data, 4)[0]
                elif version >= 1.0:
                    n_indexed = struct.unpack_from("<H", spr_data, 4)[0]
            self._act.load(act, spr_frames, n_indexed)
            self.setCurrentIndex(self._idx_act)
        except Exception as e:
            self._hex.show_bytes(act_data)
            self._hex.setPlainText(f"ACT preview failed: {e}\n\n" + self._hex.toPlainText())
            self.setCurrentIndex(self._idx_hex)

    def clear(self) -> None:
        self._act.clear()
        self.setCurrentIndex(self._idx_empty)
