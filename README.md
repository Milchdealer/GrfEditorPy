# GRF Editor Py

A Linux-native rewrite of [GRF Editor](https://github.com/Tokeiburu/GRFEditor) — the Ragnarok Online GRF container browser — in Python and PySide6.

The original GRF Editor is a great tool but Windows-only (.NET/C#). This project reimplements the core functionality so it works on Linux.

**Supported formats:** GRF v2.0, v3.0, GPF, THOR, RGZ  
**Preview support:** images (BMP, PNG, JPG, TGA), text files, SPR sprite sheets, ACT animations, hex view for everything else

![screenshot placeholder](docs/screenshot.png)

---

## Running from source

**Requirements:** Python 3.10+

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py

# Open a file directly
python main.py /path/to/data.grf
```

## Installing as a package

Install with pip to get the `grfeditorpy` command on your PATH:

```bash
pip install .

# Then run from anywhere
grfeditorpy
grfeditorpy /path/to/data.grf
```

## Building a standalone binary

Builds a self-contained binary under `dist/grfeditorpy/grfeditorpy` using PyInstaller. No Python installation needed to run the result.

```bash
make build
```

The first build downloads PySide6 and PyInstaller into `.venv-build/` and takes a few minutes. Subsequent builds reuse it and are fast.

### Desktop launcher (Linux)

After building, register the app with your desktop environment so it appears in your app launcher and can open `.grf` files by double-click:

```bash
make install-desktop
```

To remove it:

```bash
make uninstall-desktop
```

## Running tests

```bash
pytest
```

Integration tests that open a real GRF file are skipped by default. Point `TEST_GRF_PATH` at a GRF to enable them:

```bash
TEST_GRF_PATH=/path/to/data.grf pytest
```
