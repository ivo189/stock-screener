import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import CACHE_DIR, FILE_CACHE_TTL_HOURS, MEMORY_CACHE_TTL_HOURS
from models.stock import StockMetrics

logger = logging.getLogger(__name__)


def _metrics_to_dict(m: StockMetrics) -> dict:
    return m.model_dump(mode="json")


def _dict_to_metrics(d: dict) -> StockMetrics:
    return StockMetrics.model_validate(d)


class StockCache:
    def __init__(self):
        self._memory: dict[str, StockMetrics] = {}
        self._memory_ts: dict[str, datetime] = {}
        self._last_batch_update: Optional[datetime] = None
        self.memory_ttl = timedelta(hours=MEMORY_CACHE_TTL_HOURS)
        self.file_ttl = timedelta(hours=FILE_CACHE_TTL_HOURS)

    # ---- Public API ----

    def get(self, ticker: str) -> Optional[StockMetrics]:
        # Check memory first
        if ticker in self._memory:
            if datetime.utcnow() - self._memory_ts[ticker] < self.memory_ttl:
                return self._memory[ticker]
        # Check disk
        return self._load_from_disk(ticker)

    def set(self, ticker: str, data: StockMetrics) -> None:
        self._memory[ticker] = data
        self._memory_ts[ticker] = datetime.utcnow()
        self._save_to_disk(ticker, data)

    def set_batch(self, stocks: list[StockMetrics]) -> None:
        for s in stocks:
            self.set(s.ticker, s)
        self._last_batch_update = datetime.utcnow()
        self._save_batch_timestamp()

    def get_all(self) -> list[StockMetrics]:
        return list(self._memory.values())

    def cache_age_seconds(self) -> Optional[float]:
        if self._last_batch_update is None:
            return None
        return (datetime.utcnow() - self._last_batch_update).total_seconds()

    def is_stale(self) -> bool:
        age = self.cache_age_seconds()
        if age is None:
            return True
        return age > self.file_ttl.total_seconds()

    def warm_from_disk(self) -> int:
        """Load all cached tickers from disk into memory. Returns count loaded."""
        loaded = 0
        batch_ts_file = CACHE_DIR / "_batch_updated_at.txt"
        if batch_ts_file.exists():
            try:
                self._last_batch_update = datetime.fromisoformat(batch_ts_file.read_text().strip())
            except Exception:
                pass

        for f in CACHE_DIR.glob("*.json"):
            if f.stem.startswith("_") or f.stem == "sp500_tickers":
                continue
            try:
                raw = json.loads(f.read_text())
                m = _dict_to_metrics(raw)
                self._memory[m.ticker] = m
                self._memory_ts[m.ticker] = datetime.utcnow()
                loaded += 1
            except Exception as e:
                logger.warning(f"Failed to load cache file {f}: {e}")
        logger.info(f"Warmed cache with {loaded} tickers from disk.")
        return loaded

    # ---- Private helpers ----

    def _ticker_path(self, ticker: str) -> Path:
        safe = ticker.replace("/", "_").replace("\\", "_")
        return CACHE_DIR / f"{safe}.json"

    def _load_from_disk(self, ticker: str) -> Optional[StockMetrics]:
        path = self._ticker_path(ticker)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text())
            last_updated = datetime.fromisoformat(raw.get("last_updated", "2000-01-01"))
            if datetime.utcnow() - last_updated > self.file_ttl:
                return None
            m = _dict_to_metrics(raw)
            # Warm memory
            self._memory[ticker] = m
            self._memory_ts[ticker] = datetime.utcnow()
            return m
        except Exception as e:
            logger.warning(f"Disk cache read error for {ticker}: {e}")
            return None

    def _save_to_disk(self, ticker: str, data: StockMetrics) -> None:
        path = self._ticker_path(ticker)
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(_metrics_to_dict(data), default=str))
            tmp.replace(path)
        except Exception as e:
            logger.warning(f"Disk cache write error for {ticker}: {e}")

    def _save_batch_timestamp(self) -> None:
        try:
            ts_file = CACHE_DIR / "_batch_updated_at.txt"
            ts_file.write_text(datetime.utcnow().isoformat())
        except Exception:
            pass


# Singleton instance
stock_cache = StockCache()
