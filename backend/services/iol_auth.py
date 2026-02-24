"""
InvertirOnline API authentication manager.
Handles bearer token lifecycle: initial login, auto-refresh on expiry (15min TTL).
Credentials are read from environment variables IOL_USERNAME and IOL_PASSWORD.
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

IOL_TOKEN_URL = "https://api.invertironline.com/token"
# Bearer token TTL is 15 minutes; refresh 1 minute before expiry
TOKEN_TTL_SECONDS = 14 * 60  # 14 min to stay safely under the 15-min limit


@dataclass
class TokenState:
    access_token: str = ""
    refresh_token: str = ""
    obtained_at: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def is_expired(self) -> bool:
        return time.monotonic() - self.obtained_at >= TOKEN_TTL_SECONDS

    def has_token(self) -> bool:
        return bool(self.access_token)


_state = TokenState()


async def _post_token(data: dict) -> dict:
    """POST to /token endpoint with form-encoded body."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            IOL_TOKEN_URL,
            content="&".join(f"{k}={v}" for k, v in data.items()),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def _login() -> None:
    """Obtain a fresh token pair using username/password."""
    username = os.getenv("IOL_USERNAME", "")
    password = os.getenv("IOL_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(
            "IOL_USERNAME and IOL_PASSWORD environment variables must be set"
        )
    logger.info("IOL: logging in with credentials...")
    payload = {
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    data = await _post_token(payload)
    _state.access_token = data["access_token"]
    _state.refresh_token = data["refresh_token"]
    _state.obtained_at = time.monotonic()
    logger.info("IOL: login successful, token obtained.")


async def _refresh() -> None:
    """Refresh the bearer token using the stored refresh_token."""
    logger.info("IOL: refreshing token...")
    payload = {
        "refresh_token": _state.refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        data = await _post_token(payload)
        _state.access_token = data["access_token"]
        _state.refresh_token = data["refresh_token"]
        _state.obtained_at = time.monotonic()
        logger.info("IOL: token refreshed successfully.")
    except Exception as e:
        logger.warning(f"IOL: token refresh failed ({e}), falling back to full login.")
        await _login()


async def get_bearer_token() -> str:
    """
    Return a valid bearer token, refreshing or re-logging-in as needed.
    Thread-safe via asyncio.Lock to prevent concurrent auth races.
    """
    async with _state.lock:
        if not _state.has_token():
            await _login()
        elif _state.is_expired():
            if _state.refresh_token:
                await _refresh()
            else:
                await _login()
    return _state.access_token


def invalidate_token() -> None:
    """Force re-authentication on next request (call after 401 response)."""
    _state.access_token = ""
    _state.refresh_token = ""
    _state.obtained_at = 0.0
    logger.info("IOL: token invalidated, will re-login on next request.")
