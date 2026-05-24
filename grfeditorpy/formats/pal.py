"""PAL palette format → PIL Image swatch."""
from PIL import Image


def load_palette_swatch(data: bytes, swatch_size: int = 16) -> Image.Image:
    """Return a 256-color palette swatch image (16×16 blocks of swatch_size px each)."""
    if len(data) < 1024:
        return Image.new("RGBA", (1, 1))

    cell = swatch_size
    img = Image.new("RGBA", (16 * cell, 16 * cell))
    px = img.load()

    for i in range(256):
        r = data[4 * i + 0]
        g = data[4 * i + 1]
        b = data[4 * i + 2]
        a = 255 if i > 0 else 0

        row, col = divmod(i, 16)
        for dy in range(cell):
            for dx in range(cell):
                px[col * cell + dx, row * cell + dy] = (r, g, b, a)

    return img
