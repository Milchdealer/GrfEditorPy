"""File entry properties dialog."""
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QDialogButtonBox, QWidget
)
from ...core.file_entry import FileEntry


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.2f} MB ({n:,} bytes)"
    if n >= 1024:
        return f"{n / 1024:.2f} KB ({n:,} bytes)"
    return f"{n:,} bytes"


class PropertiesDialog(QDialog):
    def __init__(self, entry: FileEntry, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("File Properties")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow("Path:", QLabel(entry.relative_path))
        form.addRow("Size:", QLabel(_fmt_size(entry.size_decompressed)))
        form.addRow("Compressed:", QLabel(_fmt_size(entry.size_compressed)))
        form.addRow("Aligned:", QLabel(_fmt_size(entry.size_compressed_aligned)))
        ratio = (1 - entry.size_compressed / max(entry.size_decompressed, 1)) * 100
        form.addRow("Ratio:", QLabel(f"{ratio:.1f}%"))
        form.addRow("Offset:", QLabel(f"0x{entry.file_exact_offset:08X}"))
        form.addRow("Flags:", QLabel(f"0x{entry.flags:02X}"))
        form.addRow("Encrypted:", QLabel("Yes" if entry.is_encrypted else "No"))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
