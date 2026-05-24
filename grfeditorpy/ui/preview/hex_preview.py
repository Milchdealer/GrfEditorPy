"""Hex dump preview (first 4 KB)."""
from typing import Optional
from PySide6.QtWidgets import QTextEdit, QWidget

_PREVIEW_BYTES = 4096


def _hex_dump(data: bytes) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i: i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:08x}  {hex_part:<47}  {asc_part}")
    return "\n".join(lines)


class HexPreview(QTextEdit):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = self.font()
        font.setFamily("Monospace")
        self.setFont(font)

    def show_bytes(self, data: bytes) -> None:
        preview = data[:_PREVIEW_BYTES]
        suffix = f"\n... ({len(data) - _PREVIEW_BYTES} more bytes)" if len(data) > _PREVIEW_BYTES else ""
        self.setPlainText(_hex_dump(preview) + suffix)

    def clear(self) -> None:
        self.setPlainText("")
