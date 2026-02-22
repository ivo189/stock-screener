import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from config import CACHE_DIR, DJIA_TICKERS, NDX_TICKERS, SP500_FALLBACK, SP500_LIST_CACHE_DAYS

logger = logging.getLogger(__name__)

SP500_CACHE_FILE = CACHE_DIR / "sp500_tickers.json"


def _load_sp500_from_cache() -> Optional[list[str]]:
    if not SP500_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(SP500_CACHE_FILE.read_text())
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        if datetime.utcnow() - fetched_at < timedelta(days=SP500_LIST_CACHE_DAYS):
            return data["tickers"]
    except Exception:
        pass
    return None


def _save_sp500_to_cache(tickers: list[str]) -> None:
    try:
        tmp = SP500_CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"fetched_at": datetime.utcnow().isoformat(), "tickers": tickers}))
        tmp.replace(SP500_CACHE_FILE)
    except Exception as e:
        logger.warning(f"Could not save S&P 500 list to cache: {e}")


def get_sp500_tickers() -> list[str]:
    cached = _load_sp500_from_cache()
    if cached:
        logger.info(f"Loaded {len(cached)} S&P 500 tickers from cache.")
        return cached

    try:
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", flavor="lxml")
        df = tables[0]
        # Column is typically 'Symbol' or 'Ticker symbol'
        col = next((c for c in df.columns if "symbol" in c.lower() or "ticker" in c.lower()), df.columns[0])
        tickers = df[col].str.replace(".", "-", regex=False).tolist()
        tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
        logger.info(f"Fetched {len(tickers)} S&P 500 tickers from Wikipedia.")
        _save_sp500_to_cache(tickers)
        return tickers
    except Exception as e:
        logger.warning(f"Wikipedia S&P 500 fetch failed: {e}. Using fallback list.")
        return SP500_FALLBACK


def get_full_universe(indices: list[str]) -> list[str]:
    tickers: set[str] = set()
    if "SP500" in indices:
        tickers.update(get_sp500_tickers())
    if "DJIA" in indices:
        tickers.update(DJIA_TICKERS)
    if "NDX" in indices:
        tickers.update(NDX_TICKERS)
    return sorted(tickers)
