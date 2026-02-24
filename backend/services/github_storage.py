"""
GitHub-backed persistence for bond history.

Stores JSON files in a dedicated branch of the repo so they survive
Render deploys (which wipe the ephemeral filesystem).

Required env vars:
  GITHUB_TOKEN   — Personal Access Token with repo scope (or fine-grained with Contents: write)
  GITHUB_REPO    — e.g. "ivo189/stock-screener"
  GITHUB_BRANCH  — branch to store data files (default: "data")

Files are stored at:  data/bonds/<filename>
"""
import base64
import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO   = os.getenv("GITHUB_REPO", "ivo189/stock-screener")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "data")
_BASE = "https://api.github.com"
_DATA_PREFIX = "data/bonds"


def _enabled() -> bool:
    return bool(GITHUB_TOKEN)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _file_path(filename: str) -> str:
    return f"{_DATA_PREFIX}/{filename}"


def pull(filename: str) -> Optional[list]:
    """
    Download a JSON array from GitHub. Returns None if not found or disabled.
    Synchronous — called only at startup.
    """
    if not _enabled():
        return None
    url = f"{_BASE}/repos/{GITHUB_REPO}/contents/{_file_path(filename)}"
    try:
        r = httpx.get(url, headers=_headers(), params={"ref": GITHUB_BRANCH}, timeout=15)
        if r.status_code == 404:
            logger.info(f"GitHub storage: {filename} not found on branch '{GITHUB_BRANCH}' (first run)")
            return None
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode()
        logger.info(f"GitHub storage: pulled {filename} ({len(content)} bytes)")
        return json.loads(content)
    except Exception as e:
        logger.warning(f"GitHub storage: pull failed for {filename}: {e}")
        return None


def push(filename: str, records: list) -> None:
    """
    Upload a JSON array to GitHub (create or update). Fire-and-forget — errors are logged only.
    Synchronous — called from a background thread via asyncio.to_thread.
    """
    if not _enabled():
        return
    url = f"{_BASE}/repos/{GITHUB_REPO}/contents/{_file_path(filename)}"
    try:
        # Get current SHA (needed to update existing file)
        sha: Optional[str] = None
        r = httpx.get(url, headers=_headers(), params={"ref": GITHUB_BRANCH}, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
        elif r.status_code != 404:
            r.raise_for_status()

        content_bytes = json.dumps(records, default=str).encode()
        body: dict = {
            "message": f"chore: update bond history {filename}",
            "content": base64.b64encode(content_bytes).decode(),
            "branch": GITHUB_BRANCH,
        }
        if sha:
            body["sha"] = sha

        resp = httpx.put(url, headers=_headers(), json=body, timeout=20)
        resp.raise_for_status()
        logger.info(f"GitHub storage: pushed {filename} ({len(content_bytes)} bytes, sha={sha[:7] if sha else 'new'})")
    except Exception as e:
        logger.warning(f"GitHub storage: push failed for {filename}: {e}")
