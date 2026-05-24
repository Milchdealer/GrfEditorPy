"""TGA decoder using PIL (Pillow supports TGA natively via a BytesIO wrapper)."""
import io
from PIL import Image


def load_tga(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))
