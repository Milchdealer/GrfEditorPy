"""Main application window."""
from __future__ import annotations
import os
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QProgressBar, QStatusBar, QFileDialog,
    QMessageBox, QApplication, QMenu
)

from .folder_tree import FolderTree
from .file_list import FileList
from .preview.preview_panel import PreviewPanel
from .dialogs.extract_dialog import ExtractDialog
from .dialogs.properties_dialog import PropertiesDialog
from ..core.grf_container import GrfContainer
from ..core.file_entry import FileEntry
from ..services.extract_service import ExtractWorker
from ..services.recent_files import get_recent, add_recent


class _LoadWorker(QThread):
    loaded = Signal(object)   # GrfContainer or None
    error = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            container = GrfContainer.open(self._path)
            self.loaded.emit(container)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GRF Editor (Linux)")
        self.resize(1200, 750)

        self._container: Optional[GrfContainer] = None
        self._extract_worker: Optional[ExtractWorker] = None
        self._load_worker: Optional[_LoadWorker] = None

        self._build_ui()
        self._build_menus()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(4)

        # Search bar
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Filter:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Type to filter files…")
        self._search_edit.textChanged.connect(self._on_filter_changed)
        self._search_edit.setClearButtonEnabled(True)
        search_row.addWidget(self._search_edit)
        root_layout.addLayout(search_row)

        # 3-panel splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._folder_tree = FolderTree()
        self._folder_tree.folder_selected.connect(self._on_folder_selected)
        splitter.addWidget(self._folder_tree)

        self._file_list = FileList()
        self._file_list.entry_selected.connect(self._on_entry_selected)
        self._file_list.extract_requested.connect(self._do_extract)
        self._file_list.properties_requested.connect(self._show_properties)
        splitter.addWidget(self._file_list)

        self._preview = PreviewPanel()
        splitter.addWidget(self._preview)

        splitter.setSizes([220, 480, 480])
        root_layout.addWidget(splitter, 1)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("&File")
        act_open = QAction("&Open…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._open_file_dialog)
        file_menu.addAction(act_open)

        self._recent_menu = file_menu.addMenu("&Recent Files")
        self._recent_menu.aboutToShow.connect(self._populate_recent_menu)

        file_menu.addSeparator()
        act_close = QAction("&Close", self)
        act_close.setShortcut(QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self._close_container)
        file_menu.addAction(act_close)

        file_menu.addSeparator()
        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Edit menu
        edit_menu = mb.addMenu("&Edit")
        act_extract_sel = QAction("&Extract Selected…", self)
        act_extract_sel.setShortcut(QKeySequence("Ctrl+E"))
        act_extract_sel.triggered.connect(self._extract_selected)
        edit_menu.addAction(act_extract_sel)

        act_extract_all = QAction("Extract &All…", self)
        act_extract_all.triggered.connect(self._extract_all)
        edit_menu.addAction(act_extract_all)

        # Help menu
        help_menu = mb.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("Ready")
        self._count_label = QLabel("")
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.hide()
        sb.addWidget(self._status_label, 1)
        sb.addPermanentWidget(self._count_label)
        sb.addPermanentWidget(self._progress)

    # ------------------------------------------------------------------
    # File open / close
    # ------------------------------------------------------------------

    def open_file(self, path: str) -> None:
        self._close_container()
        self._status_label.setText(f"Loading {os.path.basename(path)}…")
        self._progress.setRange(0, 0)
        self._progress.show()

        self._load_worker = _LoadWorker(path)
        self._load_worker.loaded.connect(self._on_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.finished.connect(lambda: self._progress.hide())
        self._load_worker.start()

    def _on_loaded(self, container: GrfContainer) -> None:
        self._container = container
        add_recent(container.path)
        n = len(container.entries)
        self._count_label.setText(f"{n:,} entries")
        self._status_label.setText(os.path.basename(container.path))
        self.setWindowTitle(f"GRF Editor — {os.path.basename(container.path)}")
        self._folder_tree.load_container(container)

    def _on_load_error(self, msg: str) -> None:
        self._status_label.setText("Load failed")
        QMessageBox.critical(self, "Open Error", msg)

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GRF / GPF / THOR",
            filter="GRF archives (*.grf *.gpf *.thor *.rgz);;All files (*)"
        )
        if path:
            self.open_file(path)

    def _close_container(self) -> None:
        if self._container:
            self._container.close()
            self._container = None
        self._folder_tree.clear_container()
        self._file_list.load_entries([])
        self._preview.clear()
        self._count_label.setText("")
        self._status_label.setText("Ready")
        self.setWindowTitle("GRF Editor (Linux)")

    def _populate_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = get_recent()
        if not recent:
            self._recent_menu.addAction("(none)").setEnabled(False)
            return
        for path in recent:
            act = QAction(path, self)
            act.triggered.connect(lambda checked=False, p=path: self.open_file(p))
            self._recent_menu.addAction(act)

    # ------------------------------------------------------------------
    # Tree / list navigation
    # ------------------------------------------------------------------

    def _on_folder_selected(self, folder: str) -> None:
        if self._container is None:
            return
        entries = self._container.get_entries_in(folder)
        self._file_list.load_entries(entries)
        self._preview.clear()

    def _on_filter_changed(self, text: str) -> None:
        self._file_list.filter(text)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_entry_selected(self, entry: Optional[FileEntry]) -> None:
        if entry is None:
            self._preview.clear()
            return
        try:
            if entry.extension.lower() == ".act":
                act_data = entry.get_decompressed_data()
                spr_data = self._load_sibling_spr(entry)
                self._preview.show_act_data(act_data, spr_data)
            elif entry.extension.lower() == ".lub":
                data = entry.get_decompressed_data()
                self._preview.show_lub_data(data)
            else:
                data = entry.get_decompressed_data()
                self._preview.show_entry_data(data, entry.extension)
        except Exception as e:
            self._preview.clear()
            self._status_label.setText(f"Preview error: {e}")

    def _load_sibling_spr(self, act_entry: FileEntry) -> Optional[bytes]:
        """Find and load the .spr file with the same base name as the .act entry."""
        if self._container is None:
            return None
        act_path = act_entry.relative_path
        # Replace .act extension with .spr (case-insensitive)
        if act_path.lower().endswith(".act"):
            spr_path = act_path[:-4] + ".spr"
        else:
            return None
        spr_entry = self._container.get_entry(spr_path)
        if spr_entry is None:
            return None
        try:
            return spr_entry.get_decompressed_data()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------

    def _extract_selected(self) -> None:
        entries = self._file_list.selected_entries()
        if entries:
            self._do_extract(entries)

    def _extract_all(self) -> None:
        if self._container is None:
            return
        self._do_extract(list(self._container.entries.values()))

    def _do_extract(self, entries: list[FileEntry]) -> None:
        if not entries:
            return
        dlg = ExtractDialog(self, count=len(entries))
        if dlg.exec() != ExtractDialog.DialogCode.Accepted:
            return
        dest = dlg.dest_dir
        if not dest:
            QMessageBox.warning(self, "Extract", "Please select a destination folder.")
            return

        self._progress.setRange(0, len(entries))
        self._progress.setValue(0)
        self._progress.show()
        self._status_label.setText(f"Extracting {len(entries)} file(s)…")

        self._extract_worker = ExtractWorker(self._container, entries, dest)
        self._extract_worker.progress.connect(lambda d, t: self._progress.setValue(d))
        self._extract_worker.error.connect(
            lambda p, e: self._status_label.setText(f"Error extracting {p}: {e}")
        )
        self._extract_worker.finished_ok.connect(self._on_extract_done)
        self._extract_worker.start()

    def _on_extract_done(self, count: int) -> None:
        self._progress.hide()
        self._status_label.setText(f"Extracted {count} file(s)")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _show_properties(self, entry: FileEntry) -> None:
        PropertiesDialog(entry, self).exec()

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About GRF Editor (Linux)",
            "<b>GRF Editor (Linux)</b><br><br>"
            "A cross-platform GRF container viewer/extractor.<br>"
            "Core logic ported from the original C# GRFEditor.<br><br>"
            "Built with Python + PySide6.",
        )
