#!/bin/bash
# Start the Stock Screener frontend
export PATH="/opt/homebrew/bin:$PATH"
eval "$(fnm env --use-on-cd)"
fnm use 22

cd "$(dirname "$0")/frontend"
echo "Starting frontend on http://localhost:5173 ..."
npm run dev
