"""Center panel: file list with sortable columns."""
from typing import Optional
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QTableView, QWidget, QAbstractItemView, QHeaderView, QMenu
)
from PySide6.QtGui import QAction

from ..core.file_entry import FileEntry


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


class FileTableModel(QAbstractTableModel):
    _COLS = ["Name", "Type", "Size", "Compressed", "Offset"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[FileEntry] = []

    def set_entries(self, entries: list[FileEntry]) -> None:
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def entry_at(self, row: int) -> Optional[FileEntry]:
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._COLS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._COLS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return entry.filename
            if col == 1:
                return entry.extension.lstrip(".").upper() or "—"
            if col == 2:
                return _fmt_size(entry.size_decompressed)
            if col == 3:
                return _fmt_size(entry.size_compressed)
            if col == 4:
                return f"0x{entry.file_exact_offset:08X}"
        if role == Qt.ItemDataRole.UserRole:
            return entry
        return None


class FileList(QTableView):
    entry_selected = Signal(object)       # FileEntry or None
    extract_requested = Signal(list)      # list[FileEntry]
    properties_requested = Signal(object) # FileEntry

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._model = FileTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setModel(self._proxy)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.selectionModel().currentRowChanged.connect(self._on_current_changed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def load_entries(self, entries: list[FileEntry]) -> None:
        self._model.set_entries(entries)
        self._proxy.invalidate()

    def filter(self, text: str) -> None:
        self._proxy.setFilterKeyColumn(0)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterFixedString(text)

    def selected_entries(self) -> list[FileEntry]:
        rows = {idx.row() for idx in self.selectionModel().selectedRows()}
        result = []
        for row in sorted(rows):
            src_row = self._proxy.mapToSource(self._proxy.index(row, 0)).row()
            entry = self._model.entry_at(src_row)
            if entry:
                result.append(entry)
        return result

    def _on_current_changed(self, current, _previous) -> None:
        src = self._proxy.mapToSource(current)
        entry = self._model.entry_at(src.row())
        self.entry_selected.emit(entry)

    def _context_menu(self, pos) -> None:
        entries = self.selected_entries()
        if not entries:
            return
        menu = QMenu(self)
        act_extract = QAction(f"Extract {len(entries)} file(s)…", self)
        act_extract.triggered.connect(lambda: self.extract_requested.emit(entries))
        menu.addAction(act_extract)
        if len(entries) == 1:
            act_props = QAction("Properties…", self)
            act_props.triggered.connect(lambda: self.properties_requested.emit(entries[0]))
            menu.addAction(act_props)
        menu.exec(self.viewport().mapToGlobal(pos))
