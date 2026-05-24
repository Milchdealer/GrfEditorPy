#!/usr/bin/env bash
# build.sh — Build GRFEditorPy standalone binary via PyInstaller
# Run from: /home/jannikf/Code/GRFEditorPy/
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv-build"
DIST_DIR="$PROJECT_DIR/dist/grfeditorpy"

echo "=== GRFEditorPy Build Script ==="
echo "Project: $PROJECT_DIR"

# ── Step 1: Create build venv ───────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[1/5] Creating build venv..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install \
        "setuptools>=68" \
        "PySide6>=6.6.0" \
        "Pillow>=10.0.0" \
        "pyinstaller" \
        "pyinstaller-hooks-contrib" \
        --quiet
    echo "    Venv created."
else
    echo "[1/5] Build venv already exists."
    echo "      Delete .venv-build/ and re-run to force a fresh install."
fi

# ── Step 2: Check PyInstaller version ──────────────────────────────────────
echo "[2/5] PyInstaller version: $("$VENV_DIR/bin/pyinstaller" --version)"

# ── Step 3: Clean previous build ───────────────────────────────────────────
echo "[3/5] Cleaning previous build artifacts..."
rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist"

# ── Step 4: Run PyInstaller ────────────────────────────────────────────────
echo "[4/5] Running PyInstaller..."
cd "$PROJECT_DIR"
"$VENV_DIR/bin/pyinstaller" --noconfirm grfeditorpy.spec

# ── Step 5: Verify output ──────────────────────────────────────────────────
echo "[5/5] Verifying output..."
BINARY="$DIST_DIR/grfeditorpy"
if [[ ! -x "$BINARY" ]]; then
    echo "ERROR: Binary not found at $BINARY"
    exit 1
fi
XCB_PLUGIN=$(find "$DIST_DIR" -name "libqxcb.so" 2>/dev/null | head -1)
if [[ -z "$XCB_PLUGIN" ]]; then
    echo "WARNING: libqxcb.so not found in dist! App will fail to start."
    echo "         Check that PySide6 was installed from pip, not pacman."
else
    echo "    libqxcb.so: $XCB_PLUGIN"
fi
echo "    Total size: $(du -sh "$DIST_DIR" | cut -f1)"
echo ""
echo "=== Build complete ==="
echo "Binary: $BINARY"
echo ""
echo "To install a desktop launcher:"
echo "    make install-desktop"
echo ""
echo "To test:"
echo "    $BINARY"
