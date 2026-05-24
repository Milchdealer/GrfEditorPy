import struct
from dataclasses import dataclass

MAGIC = b"Master of Magic\x00"
HEADER_SIZE = 46


@dataclass
class GrfHeader:
    magic: bytes
    key: bytes
    file_table_offset: int
    seed: int
    files_count_raw: int
    major: int
    minor: int

    @property
    def real_files_count(self) -> int:
        return self.files_count_raw - self.seed - 7

    @property
    def version(self) -> float:
        return self.major + self.minor / 100.0

    @classmethod
    def parse(cls, data: bytes) -> "GrfHeader":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} < {HEADER_SIZE}")

        magic = data[0:16]
        key = data[16:30]
        version_word = struct.unpack_from("<i", data, 42)[0]
        major = (version_word >> 8) & 0xFF
        minor = version_word & 0xFF

        # v3.0 uses int64 file_table_offset and stores real count directly
        if major == 3 and minor == 0 and data[35] == 0 and data[36] == 0 and data[37] == 0:
            file_table_offset = struct.unpack_from("<q", data, 30)[0]
            seed = 0
            files_count_raw = struct.unpack_from("<i", data, 38)[0]
        else:
            file_table_offset = struct.unpack_from("<I", data, 30)[0]
            seed = struct.unpack_from("<i", data, 34)[0]
            files_count_raw = struct.unpack_from("<i", data, 38)[0]

        return cls(magic, key, file_table_offset, seed, files_count_raw, major, minor)
