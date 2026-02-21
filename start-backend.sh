#!/bin/bash
# Start the Stock Screener backend API
export PATH="$HOME/.local/bin:$PATH"
export PYTHONWARNINGS="ignore::urllib3.exceptions.NotOpenSSLWarning"

cd "$(dirname "$0")/backend"
echo "Starting backend on http://localhost:8000 ..."
echo "API docs available at http://localhost:8000/docs"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
