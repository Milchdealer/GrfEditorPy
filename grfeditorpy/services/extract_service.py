"""Background extraction worker using QThread."""
from __future__ import annotations
import os
from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal

from ..core.file_entry import FileEntry
from ..core.grf_container import GrfContainer


class ExtractWorker(QThread):
    progress = Signal(int, int)       # (done, total)
    file_done = Signal(str)           # extracted path
    error = Signal(str, str)          # (grf_path, error_msg)
    finished_ok = Signal(int)         # total extracted

    def __init__(self, container: GrfContainer, entries: list[FileEntry], dest_dir: str):
        super().__init__()
        self._container = container
        self._entries = entries
        self._dest_dir = dest_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._entries)
        done = 0
        for entry in self._entries:
            if self._cancelled:
                break
            try:
                path = self._container.extract_to(entry, self._dest_dir)
                self.file_done.emit(path)
            except Exception as exc:
                self.error.emit(entry.relative_path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.finished_ok.emit(done)
