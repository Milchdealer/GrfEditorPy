import json
import os

_CONFIG_DIR = os.path.expanduser("~/.config/grfeditorpy")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")
_MAX_RECENT = 10


def _load() -> dict:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(cfg: dict) -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_recent() -> list[str]:
    return _load().get("recent_files", [])


def add_recent(path: str) -> None:
    cfg = _load()
    recent = cfg.get("recent_files", [])
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    cfg["recent_files"] = recent[:_MAX_RECENT]
    _save(cfg)
