_ENCODING = "cp949"


def get_encoding() -> str:
    return _ENCODING


def set_encoding(enc: str) -> None:
    global _ENCODING
    _ENCODING = enc


def decode_filename(raw: bytes) -> str:
    for enc in (_ENCODING, "cp1252", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace")
