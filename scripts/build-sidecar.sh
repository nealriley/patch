#!/bin/bash
# Build the Python sidecar for Tauri

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building Deck Link sidecar..."

cd "$PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]" --quiet

# Build with PyInstaller
echo "Building executable with PyInstaller..."
pyinstaller \
    --onefile \
    --name deck-link-sidecar \
    --distpath "$PROJECT_DIR/ui/src-tauri/binaries" \
    --specpath "$PROJECT_DIR/build" \
    --workpath "$PROJECT_DIR/build" \
    --clean \
    --noconfirm \
    "$PROJECT_DIR/src/deck_link/main.py"

# Get the target triple for the current platform
TARGET_TRIPLE=$(rustc -vV | grep host | cut -d' ' -f2)

# Rename binary to include target triple (required by Tauri)
BINARY_PATH="$PROJECT_DIR/ui/src-tauri/binaries/deck-link-sidecar"
if [ -f "$BINARY_PATH" ]; then
    mv "$BINARY_PATH" "${BINARY_PATH}-${TARGET_TRIPLE}"
    echo "Built: ${BINARY_PATH}-${TARGET_TRIPLE}"
fi

# Make it executable
chmod +x "${BINARY_PATH}-${TARGET_TRIPLE}"

echo "Sidecar build complete!"
