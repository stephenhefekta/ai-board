#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing build deps…"
python3 -m pip install pywebview pyinstaller pillow --quiet

echo "Generating icon…"
python3 make_icon.py

echo "Building .app…"
python3 -m PyInstaller \
  --windowed \
  --name "AI Board" \
  --icon "AI Board.icns" \
  --add-data "static:static" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --collect-all webview \
  --noconfirm \
  main.py

echo ""
echo "✓ Done: dist/AI Board.app"
echo "  Drag it to /Applications to install."
