from __future__ import annotations
import os
import threading
from typing import Optional

from .grf_header import GrfHeader, HEADER_SIZE, MAGIC
from .file_table import parse_file_table
from .file_entry import FileEntry


class GrfContainer:
    def __init__(
        self,
        path: str,
        header: GrfHeader,
        entries: dict[str, FileEntry],
        _stream,
        _lock,
    ) -> None:
        self.path = path
        self.header = header
        self._entries = entries   # lower-case key → FileEntry
        self._stream = _stream
        self._lock = _lock

    @classmethod
    def open(cls, path: str, encoding: Optional[str] = None) -> "GrfContainer":
        from .encoding import set_encoding
        if encoding:
            set_encoding(encoding)

        stream = open(path, "rb")
        lock = threading.Lock()

        raw_header = stream.read(HEADER_SIZE)
        header = GrfHeader.parse(raw_header)

        if header.magic[:15] != MAGIC[:15]:
            stream.close()
            raise ValueError(f"Not a GRF file (bad magic): {path}")

        if header.major == 2 or (header.major == 1 and header.minor >= 2):
            version = 200 if header.major == 2 else 100
        elif header.major == 3:
            version = 300
        else:
            version = 200  # best-effort fallback

        entries = parse_file_table(stream, header.file_table_offset, version, lock)
        container = cls(path, header, entries, stream, lock)
        container._build_index()
        return container

    def close(self) -> None:
        if self._stream and not self._stream.closed:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @property
    def entries(self) -> dict[str, FileEntry]:
        return self._entries

    def get_entry(self, path: str) -> Optional[FileEntry]:
        return self._entries.get(path.lower())

    def _build_index(self) -> None:
        subfolders: dict[str, set[str]] = {"": set()}
        folder_files: dict[str, list[FileEntry]] = {"": []}

        for entry in self._entries.values():
            path = entry.relative_path.replace("/", "\\")
            parts = path.split("\\")
            acc = ""
            for part in parts[:-1]:
                parent = acc
                acc = (acc + "\\" + part if acc else part).lower()
                parent_lower = parent.lower()
                if acc not in subfolders:
                    subfolders[acc] = set()
                    folder_files[acc] = []
                if parent_lower not in subfolders:
                    subfolders[parent_lower] = set()
                subfolders[parent_lower].add(acc.split("\\")[-1])
            parent_key = "\\".join(parts[:-1]).lower()
            folder_files.setdefault(parent_key, []).append(entry)

        self._subfolders: dict[str, list[str]] = {
            k: sorted(v) for k, v in subfolders.items()
        }
        self._folder_files: dict[str, list[FileEntry]] = {
            k: sorted(v, key=lambda e: e.filename.lower())
            for k, v in folder_files.items()
        }

    def get_folders(self) -> list[str]:
        """Return sorted unique folder paths present in the GRF."""
        return sorted(self._subfolders.keys())

    def get_entries_in(self, folder: str) -> list[FileEntry]:
        """Return files directly inside a folder (non-recursive)."""
        key = folder.strip("\\").lower()
        return self._folder_files.get(key, [])

    def get_subfolders(self, folder: str) -> list[str]:
        """Return immediate child folder names under folder."""
        key = folder.strip("\\").lower()
        return self._subfolders.get(key, [])

    def extract_entry(self, entry: FileEntry, dest_path: str) -> None:
        """Decompress entry and write to dest_path."""
        data = entry.get_decompressed_data()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)

    def extract_to(self, entry: FileEntry, dest_dir: str) -> str:
        """Extract entry preserving its GRF path under dest_dir."""
        rel = entry.relative_path.replace("\\", os.sep)
        dest_path = os.path.join(dest_dir, rel)
        self.extract_entry(entry, dest_path)
        return dest_path
