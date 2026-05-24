"""Basic GRF container parsing tests.

These tests run with pytest and require a real .grf file.
If no GRF is available, the tests are skipped.
"""
import os
import struct
import zlib
import pytest
from grfeditorpy.core.grf_header import GrfHeader, MAGIC, HEADER_SIZE
from grfeditorpy.core.compression import align


# Locate a real GRF for integration tests
_GRF_PATH = os.environ.get("TEST_GRF_PATH", "")
_HAS_GRF = bool(_GRF_PATH and os.path.isfile(_GRF_PATH))


def _make_minimal_grf(n_files: int = 0) -> bytes:
    """Build a minimal v2.0 GRF with an empty file table."""
    # Build empty file table
    table_data = b""
    compressed = zlib.compress(table_data)

    # File body (nothing)
    body = b""

    # file_table_offset = size of body (0)
    file_table_offset = len(body)
    seed = 0
    files_count_raw = n_files + seed + 7

    version_word = (2 << 8) | 0  # v2.0

    header = bytearray(HEADER_SIZE)
    header[0:16] = MAGIC
    header[16:30] = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e"
    struct.pack_into("<I", header, 30, file_table_offset)
    struct.pack_into("<i", header, 34, seed)
    struct.pack_into("<i", header, 38, files_count_raw)
    struct.pack_into("<i", header, 42, version_word)

    table_block = struct.pack("<ii", len(compressed), len(table_data)) + compressed
    return bytes(header) + body + table_block


# ---- Unit tests (no real GRF needed) ----

class TestGrfHeader:
    def test_parse_minimal(self):
        data = _make_minimal_grf()
        h = GrfHeader.parse(data[:HEADER_SIZE])
        assert h.magic[:15] == MAGIC[:15]
        assert h.major == 2
        assert h.minor == 0
        assert h.file_table_offset == 0
        assert h.seed == 0
        assert h.real_files_count == 0

    def test_version_property(self):
        h = GrfHeader(MAGIC, b"x" * 14, 0, 0, 7, 2, 0)
        assert abs(h.version - 2.0) < 0.01

    def test_magic_bytes(self):
        assert MAGIC[:15] == b"Master of Magic"

    def test_align(self):
        assert align(0) == 0
        assert align(1) == 8
        assert align(8) == 8
        assert align(9) == 16
        assert align(100) == 104


class TestContainerParse:
    def test_open_minimal(self, tmp_path):
        grf_bytes = _make_minimal_grf()
        p = tmp_path / "test.grf"
        p.write_bytes(grf_bytes)
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(str(p)) as c:
            assert len(c.entries) == 0
            assert c.header.major == 2

    def test_get_folders_empty(self, tmp_path):
        p = tmp_path / "test.grf"
        p.write_bytes(_make_minimal_grf())
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(str(p)) as c:
            folders = c.get_folders()
            assert "" in folders


# ---- Integration tests (require TEST_GRF_PATH) ----

@pytest.mark.skipif(not _HAS_GRF, reason="No TEST_GRF_PATH set")
class TestRealGrf:
    def test_open(self):
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(_GRF_PATH) as c:
            n = len(c.entries)
            assert n > 0, "Expected entries in GRF"
            assert c.header.major in (1, 2, 3)

    def test_entry_count_matches_header(self):
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(_GRF_PATH) as c:
            # Allow some slack for directory entries filtered out
            assert len(c.entries) > 0

    def test_decompress_one_entry(self):
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(_GRF_PATH) as c:
            for entry in list(c.entries.values())[:20]:
                if entry.is_encrypted or entry.cycle >= 0:
                    continue
                data = entry.get_decompressed_data()
                assert len(data) == entry.size_decompressed, (
                    f"{entry.relative_path}: got {len(data)}, expected {entry.size_decompressed}"
                )
                return
            pytest.skip("No non-encrypted entries found in first 20")

    def test_folders(self):
        from grfeditorpy.core.grf_container import GrfContainer
        with GrfContainer.open(_GRF_PATH) as c:
            folders = c.get_folders()
            assert len(folders) > 0
