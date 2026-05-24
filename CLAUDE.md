# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python main.py
python main.py /path/to/file.grf   # open file directly

# Run tests (unit tests need no GRF file; integration tests do)
pytest
TEST_GRF_PATH=/path/to/data.grf pytest   # enables integration tests

# Run a single test
pytest tests/test_grf_container.py::TestGrfHeader::test_parse_minimal

# Build standalone binary (creates dist/grfeditorpy/grfeditorpy)
make build         # or: bash build.sh

# Install desktop launcher (requires build first)
make install-desktop

# Verify build
make verify
```

The first `make build` creates `.venv-build/` with pip-installed PySide6 and PyInstaller (takes several minutes). Subsequent builds reuse it and are fast.

## Architecture

### GRF parsing pipeline

`GrfContainer.open()` (`core/grf_container.py`) is the entry point for all file I/O:
1. Reads the 46-byte header via `GrfHeader.parse()` (`core/grf_header.py`)
2. Parses the compressed file table via `parse_file_table()` (`core/file_table.py`) — returns a `dict[str, FileEntry]` keyed by lower-cased path
3. Builds an in-memory folder index (`_subfolders`, `_folder_files`) for O(1) tree navigation
4. Keeps the file stream open; `FileEntry.get_decompressed_data()` seeks into it lazily (thread-safe via a shared `threading.Lock`)

Compression dispatch in `FileEntry.get_decompressed_data()` detects type from the first byte: `0x00` → LZMA, `0x78` → zlib, `FLAG_LZSS` flag → LZSS, `FLAG_RAW` → uncompressed. All decompressors live in `core/compression.py`.

Supported formats: GRF v2.0 (4-byte offset), v3.0 (8-byte offset), GPF, THOR, RGZ. Gravity-encrypted and DES-encrypted entries raise `RuntimeError` (not implemented).

### GUI structure

Three-panel `QSplitter` (FolderTree | FileList | PreviewPanel) built in `MainWindow._build_ui()`:

- **FolderTree** (`ui/folder_tree.py`) — navigates `GrfContainer.get_subfolders()` / `get_folders()`; emits `folder_selected(str)`
- **FileList** (`ui/file_list.py`) — shows entries from `GrfContainer.get_entries_in(folder)`; supports filter, context-menu extract, properties; emits `entry_selected(FileEntry)`
- **PreviewPanel** (`ui/preview/preview_panel.py`) — a `QStackedWidget` that switches between sub-panels based on `preview_service.get_preview_type(extension)`: image, text, hex, spr, act

### Threading model

Two `QThread` workers in `MainWindow`:
- `_LoadWorker` — opens the GRF and emits `loaded(GrfContainer)` or `error(str)` on completion
- `ExtractWorker` (`services/extract_service.py`) — extracts entries in background, emits `progress(done, total)` and `finished_ok(count)`

The file stream is shared between the UI thread (preview) and ExtractWorker via the lock stored on each `FileEntry`.

### Format parsers

`formats/` contains pure-Python parsers for Ragnarok-specific formats consumed only by the preview layer:
- `spr.py` — SPR sprite sheets (BGRA/indexed frames → PIL images)
- `act.py` — ACT animation files (frame sequences referencing SPR frames); the preview widget (`ui/preview/act_preview.py`) loads the paired `.spr` via `MainWindow._load_sibling_spr()`
- `tga.py`, `pal.py` — TGA images and PAL palettes
- `lub.py` — LUB (compiled Lua) detection and decompilation; `is_binary()` checks for the `\x1bLua` magic header (with null-byte fallback), `decompile()` shells out to `unluac` or `luadec` if available and returns a helpful install message otherwise

### LUB file preview

`.lub` files are handled specially in `MainWindow._on_entry_selected()` (like `.act`):
- If the data is plain text Lua source → shown directly in the text preview
- If binary Lua bytecode → `unluac` (or `luadec`) is called via subprocess to decompile it; the result is shown as text

**Install the decompiler** (required for binary `.lub` files):
```bash
yay -S unluac   # AUR package; installs unluac.jar + a wrapper shell script
```
With `unluac` on PATH, binary `.lub` files decompile automatically on preview. Without it, a comment block explains what to install.
