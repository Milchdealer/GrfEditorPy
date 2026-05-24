from __future__ import annotations
import struct
import zlib
from typing import IO

from .file_entry import FileEntry, FLAG_FILE, FLAG_MIXED_ENC, FLAG_DES_ENC, FLAG_GRAVITY_ENC, FLAG_RAW, FLAG_LZSS


def parse_file_table(
    stream: IO[bytes],
    file_table_offset: int,
    version: int,
    lock: object,
) -> dict[str, FileEntry]:
    """Read and parse the compressed file table.
    Returns a dict mapping lower-case path → FileEntry (files only)."""
    from .grf_header import HEADER_SIZE

    stream.seek(HEADER_SIZE + file_table_offset)

    if version == 300:
        stream.read(4)  # unknown 4 bytes, always 0

    table_compressed_size = struct.unpack("<i", stream.read(4))[0]
    table_size = struct.unpack("<i", stream.read(4))[0]

    if table_compressed_size == 0 or table_size == 0:
        return {}

    compressed_data = stream.read(table_compressed_size)
    table_data = zlib.decompress(compressed_data)

    entries: dict[str, FileEntry] = {}
    pos = 0
    buf_len = len(table_data)

    while pos < buf_len:
        entry, pos = FileEntry.parse_from_table(table_data, pos, stream, lock, version)

        # Include files and encrypted files; skip plain directories
        is_entry = bool(entry.flags & (FLAG_FILE | FLAG_MIXED_ENC | FLAG_DES_ENC | FLAG_GRAVITY_ENC | FLAG_RAW | FLAG_LZSS))
        # Also include directories that have an extension (treated as files by the C# code)
        if not is_entry and "." in entry.filename:
            is_entry = True

        if is_entry:
            key = entry.relative_path.lower()
            if key not in entries:
                entries[key] = entry

    return entries
