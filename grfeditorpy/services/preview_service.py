"""Map file extension → preview widget type."""

IMAGE_EXTS = {".bmp", ".png", ".jpg", ".jpeg", ".gif", ".tga", ".ebm", ".pcx"}
TEXT_EXTS = {".txt", ".xml", ".lua", ".ini", ".cfg", ".log", ".json", ".csv",
             ".htm", ".html", ".py", ".js", ".ts", ".md"}
SPR_EXTS = {".spr"}
ACT_EXTS = {".act"}
PAL_EXTS = {".pal"}


def get_preview_type(extension: str) -> str:
    """Return one of: 'image', 'text', 'spr', 'act', 'pal', 'hex'."""
    ext = extension.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in TEXT_EXTS:
        return "text"
    if ext in SPR_EXTS:
        return "spr"
    if ext in ACT_EXTS:
        return "act"
    if ext in PAL_EXTS:
        return "pal"
    return "hex"
