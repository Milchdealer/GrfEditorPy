"""Left panel: folder tree view."""
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ..core.grf_container import GrfContainer

_PLACEHOLDER = "__placeholder__"


class FolderTree(QTreeWidget):
    folder_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setHeaderLabel("Folders")
        self.setColumnCount(1)
        self._container: Optional[GrfContainer] = None
        self.itemSelectionChanged.connect(self._on_selection)
        self.itemExpanded.connect(self._on_item_expanded)

    def load_container(self, container: GrfContainer) -> None:
        self._container = container
        self.clear()
        root = QTreeWidgetItem(self, ["(root)"])
        root.setData(0, 256, "")
        self._populate_children(root, "")
        root.setExpanded(True)
        self.setCurrentItem(root)

    def _populate_children(self, parent: QTreeWidgetItem, path: str) -> None:
        if self._container is None:
            return
        for sub in self._container.get_subfolders(path):
            full = path + "\\" + sub if path else sub
            item = QTreeWidgetItem(parent, [sub])
            item.setData(0, 256, full)
            if self._container.get_subfolders(full):
                QTreeWidgetItem(item, [_PLACEHOLDER])

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.childCount() == 1 and item.child(0).text(0) == _PLACEHOLDER:
            item.takeChild(0)
            self._populate_children(item, item.data(0, 256))

    def _on_selection(self) -> None:
        items = self.selectedItems()
        if items:
            path = items[0].data(0, 256)
            self.folder_selected.emit(path if path is not None else "")

    def clear_container(self) -> None:
        self._container = None
        self.clear()
