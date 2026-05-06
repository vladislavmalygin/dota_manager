#!/usr/bin/env bash
# Local Linux build script. Requires python3.11 and pyinstaller.
set -e

PYTHON=${PYTHON:-python3.11}
VENV=".venv-build"

echo "==> Using Python: $($PYTHON --version)"
echo "==> Creating build venv..."
$PYTHON -m venv "$VENV"
source "$VENV/bin/activate"

echo "==> Installing dependencies..."
pip install --upgrade pip wheel
pip install -r requirements-game.txt
pip install pyinstaller

echo "==> Building..."
pyinstaller dota_manager.spec --distpath dist/linux --workpath build/linux --clean

echo "==> Packaging..."
cd dist/linux
tar -czf ../../dota_manager_linux.tar.gz dota_manager/
cd ../..

echo ""
echo "Done: dota_manager_linux.tar.gz"
echo "Run with: ./dist/linux/dota_manager/dota_manager"
