"""Read-only text preview widget."""
from typing import Optional
from PySide6.QtWidgets import QTextEdit, QWidget


class TextPreview(QTextEdit):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = self.font()
        font.setFamily("Monospace")
        self.setFont(font)

    def show_bytes(self, data: bytes) -> None:
        for enc in ("utf-8", "cp949", "cp1252", "latin-1"):
            try:
                text = data.decode(enc)
                self.setPlainText(text)
                return
            except (UnicodeDecodeError, LookupError):
                continue
        self.setPlainText(data.decode("latin-1", errors="replace"))

    def clear(self) -> None:
        self.setPlainText("")
