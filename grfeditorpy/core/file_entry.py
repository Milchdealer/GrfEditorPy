from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import IO, Optional

from .compression import decompress_zlib, decompress_lzma, decompress_lzss

# EntryType flags (from GRF/ContainerFormat/EntryType.cs)
FLAG_FILE = 0x01
FLAG_MIXED_ENC = 0x02       # FileAndHeaderCrypted
FLAG_DES_ENC = 0x04         # FileAndDataCrypted
FLAG_LZSS = 0x08
FLAG_RAW = 0x10             # RawDataFile (uncompressed)
FLAG_LZMA = 0x20            # LzmaCompressed (set at runtime)
FLAG_GRAVITY_ENC = 0x80     # GravityEncryptedFile
FLAG_DIR = 0x00             # Directory (flags == 0)

ENTRY_STRUCT_SIZE = 17      # bytes after null terminator for v2.0 entries


@dataclass
class FileEntry:
    relative_path: str
    size_compressed: int
    size_compressed_aligned: int
    size_decompressed: int
    flags: int
    file_exact_offset: int
    cycle: int = field(default=-1, repr=False)
    _stream: Optional[IO[bytes]] = field(default=None, repr=False)
    _stream_lock: object = field(default=None, repr=False)

    @property
    def is_file(self) -> bool:
        return bool(self.flags & FLAG_FILE) or self.flags in (FLAG_MIXED_ENC, FLAG_DES_ENC)

    @property
    def is_encrypted(self) -> bool:
        return bool(self.flags & (FLAG_MIXED_ENC | FLAG_DES_ENC | FLAG_GRAVITY_ENC))

    @property
    def is_gravity_encrypted(self) -> bool:
        return bool(self.flags & FLAG_GRAVITY_ENC)

    @property
    def extension(self) -> str:
        dot = self.relative_path.rfind(".")
        return self.relative_path[dot:].lower() if dot != -1 else ""

    @property
    def filename(self) -> str:
        sep = max(self.relative_path.rfind("\\"), self.relative_path.rfind("/"))
        return self.relative_path[sep + 1:]

    def get_decompressed_data(self) -> bytes:
        if self.size_decompressed == 0:
            return b""

        if self.is_gravity_encrypted:
            raise RuntimeError(f"Gravity-encrypted entry not supported: {self.relative_path}")

        import threading
        lock = self._stream_lock if self._stream_lock else threading.Lock()
        with lock:
            self._stream.seek(self.file_exact_offset)
            data = self._stream.read(self.size_compressed_aligned)

        if self.is_encrypted:
            raise RuntimeError(f"Encrypted entry not supported: {self.relative_path}")

        # v1.x DES-scrambled filenames (Cycle >= 0) — not supported in MVP
        if self.cycle >= 0:
            raise RuntimeError(f"DES-encrypted v1.x entry not supported: {self.relative_path}")

        # LZSS (v0.18 alpha GRFs)
        if self.flags & FLAG_LZSS:
            return decompress_lzss(data, self.size_decompressed)

        # Raw (uncompressed)
        if self.flags & FLAG_RAW:
            return data[:self.size_decompressed]

        if not data:
            return b""

        # LZMA: leading 0x00 byte marker
        if data[0] == 0x00:
            return decompress_lzma(data, self.size_decompressed)

        # Standard zlib (0x78 = zlib magic)
        if data[0] == 0x78:
            return decompress_zlib(data)

        raise RuntimeError(
            f"Unknown compression for {self.relative_path!r}: "
            f"first byte 0x{data[0]:02x}, size_compressed={self.size_compressed}"
        )

    @staticmethod
    def parse_from_table(buf: bytes, pos: int, stream: IO[bytes],
                         lock: object, version: int = 200) -> tuple[FileEntry, int]:
        """Parse one FileEntry from the decompressed file table buffer.
        Returns (entry, new_pos)."""
        from .encoding import decode_filename

        end = buf.index(b"\x00", pos)
        raw_name = buf[pos:end]
        name = decode_filename(raw_name).replace("/", "\\")
        pos = end + 1

        size_compressed = struct.unpack_from("<i", buf, pos)[0]
        size_aligned = struct.unpack_from("<i", buf, pos + 4)[0]
        size_decompressed = struct.unpack_from("<i", buf, pos + 8)[0]
        flags = buf[pos + 12]

        if version == 300:
            offset_raw = struct.unpack_from("<q", buf, pos + 13)[0]
            entry_size = 21
        else:
            offset_raw = struct.unpack_from("<I", buf, pos + 13)[0]
            entry_size = ENTRY_STRUCT_SIZE

        from .grf_header import HEADER_SIZE
        file_exact_offset = offset_raw + HEADER_SIZE
        pos += entry_size

        # Determine cycle for v1.x DES encryption
        cycle = -1
        if flags == FLAG_MIXED_ENC:
            cycle = 1
            i = 10
            while size_compressed >= i:
                cycle += 1
                i *= 10
        elif flags == FLAG_DES_ENC:
            cycle = 0

        entry = FileEntry(
            relative_path=name,
            size_compressed=size_compressed,
            size_compressed_aligned=size_aligned,
            size_decompressed=size_decompressed,
            flags=flags,
            file_exact_offset=file_exact_offset,
            cycle=cycle,
            _stream=stream,
            _stream_lock=lock,
        )
        return entry, pos
