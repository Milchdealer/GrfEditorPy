import zlib
import lzma as _lzma


def decompress_zlib(data: bytes) -> bytes:
    return zlib.decompress(data)


def decompress_lzma(data: bytes, expected_size: int) -> bytes:
    # GRF LZMA entries: first byte is 0x00, rest is LZMA-compressed data
    # The LZMA data uses the legacy 5-byte props + 8-byte size header format
    raw = data[1:]  # strip the leading 0x00 marker
    try:
        return _lzma.decompress(raw, format=_lzma.FORMAT_ALONE)
    except Exception:
        # Fallback: try raw format
        return _lzma.decompress(raw)


def decompress_lzss(data: bytes, expected_size: int) -> bytes:
    """LZSS decompression used by v0.18 (alpha) GRFs."""
    out = bytearray(expected_size)
    src = 0
    dst = 0
    while src < len(data) and dst < expected_size:
        flag = data[src]
        src += 1
        for bit in range(8):
            if dst >= expected_size:
                break
            if flag & (1 << bit):
                if src >= len(data):
                    break
                out[dst] = data[src]
                src += 1
                dst += 1
            else:
                if src + 1 >= len(data):
                    break
                b0 = data[src]
                b1 = data[src + 1]
                src += 2
                length = (b1 & 0x0F) + 3
                offset = b0 | ((b1 & 0xF0) << 4)
                if offset == 0:
                    break
                for _ in range(length):
                    if dst >= expected_size:
                        break
                    out[dst] = out[dst - offset]
                    dst += 1
    return bytes(out)


def align(size: int) -> int:
    remainder = size % 8
    return size + (8 - remainder) if remainder else size
