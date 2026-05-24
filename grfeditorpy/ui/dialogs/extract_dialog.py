"""Extract dialog: choose destination directory."""
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QDialogButtonBox, QWidget
)


class ExtractDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, count: int = 1, default_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Extract Files")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Extract {count} file(s) to:"))

        row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select destination folder…")
        if default_dir:
            self._path_edit.setText(default_dir)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        row.addWidget(self._path_edit, 1)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select destination")
        if path:
            self._path_edit.setText(path)

    @property
    def dest_dir(self) -> str:
        return self._path_edit.text().strip()
