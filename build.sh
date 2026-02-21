#!/bin/bash
# Build script: compiles React frontend and copies to backend/static/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Building frontend ==="
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

# Try fnm first, then fallback to system node
if command -v fnm &>/dev/null; then
  eval "$(fnm env --use-on-cd)" 2>/dev/null || true
  fnm use 22 2>/dev/null || true
fi

cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run build

echo "=== Copying frontend to backend/static/ ==="
rm -rf "$SCRIPT_DIR/backend/static"
cp -r "$SCRIPT_DIR/frontend/dist" "$SCRIPT_DIR/backend/static"

echo "=== Build complete ==="
echo "Frontend available at backend/static/"
