"""SPR sprite format parser → PIL Image.

Reference: GRF/FileFormats/SprFormat/SprLoader.cs
"""
from __future__ import annotations
import struct
import zlib
from typing import Optional
from PIL import Image


def _rle_decompress(data: bytes, width: int, height: int) -> bytes:
    """RLE used for Indexed8 frames in SPR v2.1+."""
    out = bytearray(width * height)
    pos = 0
    src = 0
    while src < len(data):
        b = data[src]
        src += 1
        if b == 0:
            if src < len(data):
                pos += data[src]
                src += 1
        else:
            if pos < len(out):
                out[pos] = b
            pos += 1
    return bytes(out)


def _bgra32_flip(data: bytes, width: int, height: int) -> bytes:
    """Flip vertical and reorder B,G,R,A → R,G,B,A for PIL.
    Source is stored bottom-to-top with channels in BGRA order."""
    out = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            src_idx = 4 * ((height - y - 1) * width + x)
            dst_idx = 4 * (y * width + x)
            out[dst_idx + 0] = data[src_idx + 2]  # R
            out[dst_idx + 1] = data[src_idx + 1]  # G
            out[dst_idx + 2] = data[src_idx + 0]  # B
            out[dst_idx + 3] = data[src_idx + 3]  # A
    return bytes(out)


def load_first_frame(data: bytes) -> Optional[Image.Image]:
    """Decode the first frame of an SPR file. Returns a PIL RGBA Image or None."""
    if len(data) < 4 or data[0:2] != b"SP":
        return None

    minor = data[2]
    major = data[3]
    version = major + minor * 0.1

    pos = 4
    if version >= 2.0:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
    elif version >= 1.0:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = 0
        pos += 2
    else:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4

    total = n_indexed + n_bgra32
    if total == 0:
        return None

    # Parse the first frame only
    width = struct.unpack_from("<H", data, pos)[0]
    height = struct.unpack_from("<H", data, pos + 2)[0]
    pos += 4

    if width == 0 or height == 0:
        return None

    if n_indexed > 0:
        # Indexed8 frame
        if version >= 2.2:
            frame_len = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            frame_data = data[pos: pos + frame_len]
            pos += frame_len
        elif version >= 2.1:
            frame_len = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            frame_data = data[pos: pos + frame_len]
            pos += frame_len
        else:
            frame_data = data[pos: pos + width * height]

        pixels = _rle_decompress(frame_data, width, height) if version >= 2.1 else frame_data

        # Palette is the last 1024 bytes of the file
        pal_raw = data[-1024:]
        palette = bytearray(pal_raw)
        # Force all alpha to 255; first color is transparent
        for i in range(256):
            palette[4 * i + 3] = 255
        palette[3] = 0  # first color transparent

        img = Image.frombytes("P", (width, height), pixels)
        # Convert palette from RGBA to RGB for PIL putpalette
        pal_rgb = bytearray(256 * 3)
        for i in range(256):
            pal_rgb[3 * i + 0] = palette[4 * i + 0]
            pal_rgb[3 * i + 1] = palette[4 * i + 1]
            pal_rgb[3 * i + 2] = palette[4 * i + 2]
        img.putpalette(pal_rgb)
        img = img.convert("RGBA")
        # Make first palette index transparent
        px = img.load()
        p_r, p_g, p_b = pal_rgb[0], pal_rgb[1], pal_rgb[2]
        # Use palette index 0 transparency via the alpha channel we set to 0 above
        # Re-apply from raw pixels
        raw_pixels = list(img.getdata())
        for idx, pix_val in enumerate(pixels):
            if pix_val == 0:
                x_ = idx % width
                y_ = idx // width
                px[x_, y_] = (px[x_, y_][0], px[x_, y_][1], px[x_, y_][2], 0)
        return img

    else:
        # BGRA32 frame
        if version >= 3.2:
            raw_len = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            compressed = data[pos: pos + raw_len]
            frame_data = zlib.decompress(compressed)
        else:
            frame_data = data[pos: pos + width * height * 4]

        rgba = _bgra32_flip(frame_data, width, height)
        return Image.frombytes("RGBA", (width, height), rgba)


def load_all_frames(data: bytes) -> list[Image.Image]:
    """Decode all frames of an SPR file. Returns a list of PIL RGBA Images."""
    if len(data) < 4 or data[0:2] != b"SP":
        return []

    minor = data[2]
    major = data[3]
    version = major + minor * 0.1

    pos = 4
    if version >= 2.0:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
    elif version >= 1.0:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = 0
        pos += 2
    else:
        n_indexed = struct.unpack_from("<H", data, pos)[0]
        n_bgra32 = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4

    raw_frames = []

    # Read indexed8 frames
    for _ in range(n_indexed):
        w = struct.unpack_from("<H", data, pos)[0]
        h = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
        if version >= 2.2:
            fl = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            fd = data[pos: pos + fl]
            pos += fl
        elif version >= 2.1:
            fl = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            fd = data[pos: pos + fl]
            pos += fl
        else:
            fl = w * h
            fd = data[pos: pos + fl]
            pos += fl
        raw_frames.append(("idx8", w, h, fd))

    # Read bgra32 frames
    for _ in range(n_bgra32):
        w = struct.unpack_from("<H", data, pos)[0]
        h = struct.unpack_from("<H", data, pos + 2)[0]
        pos += 4
        if version >= 3.2:
            rl = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            fd = zlib.decompress(data[pos: pos + rl])
            pos += rl
        else:
            fd = data[pos: pos + w * h * 4]
            pos += w * h * 4
        raw_frames.append(("bgra32", w, h, fd))

    # Palette
    palette = None
    if n_indexed > 0:
        pal_raw = data[-1024:]
        palette = bytearray(pal_raw)
        for i in range(256):
            palette[4 * i + 3] = 255
        palette[3] = 0

    images = []
    for i, (kind, w, h, fd) in enumerate(raw_frames):
        if w == 0 or h == 0:
            images.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            continue
        if kind == "idx8":
            pixels = _rle_decompress(fd, w, h) if version >= 2.1 else fd
            img = Image.frombytes("P", (w, h), pixels)
            pal_rgb = bytearray(256 * 3)
            for j in range(256):
                pal_rgb[3 * j] = palette[4 * j]
                pal_rgb[3 * j + 1] = palette[4 * j + 1]
                pal_rgb[3 * j + 2] = palette[4 * j + 2]
            img.putpalette(pal_rgb)
            img = img.convert("RGBA")
            px = img.load()
            for idx, pv in enumerate(pixels):
                if pv == 0:
                    px[idx % w, idx // w] = (px[idx % w, idx // w][0], px[idx % w, idx // w][1], px[idx % w, idx // w][2], 0)
        else:
            rgba = _bgra32_flip(fd, w, h)
            img = Image.frombytes("RGBA", (w, h), rgba)
        images.append(img)

    return images
