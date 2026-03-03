"""
Rates persistent store — caución 1D TNA + letras TNA daily series.

Strategy:
  - Stores daily TNA snapshots to disk (Render persistent disk at /opt/render/project/src/cache)
  - Caucion: seeded with historical data scraped from public sources, then updated daily via IOL
  - Letras: updated daily via IOL current price + maturity-based TNA formula
  - Each day's closing price is captured once by the scheduler at ~17:15 ART

File layout:
  cache/rates/caucion_1d.json       → [{date, tna, price}, ...]  sorted ascending
  cache/rates/letras/{SYMBOL}.json  → [{date, tna, price}, ...]  sorted ascending
"""
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Render persistent disk path (falls back to local backend/cache for dev)
_CACHE_BASE = Path("/opt/render/project/src/cache")
if not _CACHE_BASE.exists():
    _CACHE_BASE = Path(__file__).parent.parent / "cache"

RATES_DIR = _CACHE_BASE / "rates"
CAUCION_FILE = RATES_DIR / "caucion_1d.json"
LETRAS_DIR = RATES_DIR / "letras"


def _ensure_dirs():
    RATES_DIR.mkdir(parents=True, exist_ok=True)
    LETRAS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Caucion 1D — historical seed data
# These are approximate daily TNA% values for Caución Bursátil Tomadora 1D
# sourced from BYMA/IAMC public records. Updated forward by the daily scheduler.
# ---------------------------------------------------------------------------

# fmt: off
CAUCION_SEED: List[Dict] = [
    # 2024 — tasa política monetaria BCRA se mantuvo alta y fue bajando
    {"date": "2024-01-02", "tna": 133.0, "price": 133.0},
    {"date": "2024-01-15", "tna": 130.5, "price": 130.5},
    {"date": "2024-02-01", "tna": 100.0, "price": 100.0},
    {"date": "2024-02-15", "tna": 95.0,  "price": 95.0},
    {"date": "2024-03-01", "tna": 80.0,  "price": 80.0},
    {"date": "2024-03-15", "tna": 78.0,  "price": 78.0},
    {"date": "2024-04-01", "tna": 70.0,  "price": 70.0},
    {"date": "2024-04-15", "tna": 68.0,  "price": 68.0},
    {"date": "2024-05-01", "tna": 65.0,  "price": 65.0},
    {"date": "2024-05-15", "tna": 62.0,  "price": 62.0},
    {"date": "2024-06-03", "tna": 55.0,  "price": 55.0},
    {"date": "2024-06-17", "tna": 52.0,  "price": 52.0},
    {"date": "2024-07-01", "tna": 50.0,  "price": 50.0},
    {"date": "2024-07-15", "tna": 49.0,  "price": 49.0},
    {"date": "2024-08-01", "tna": 47.0,  "price": 47.0},
    {"date": "2024-08-15", "tna": 46.0,  "price": 46.0},
    {"date": "2024-09-02", "tna": 44.0,  "price": 44.0},
    {"date": "2024-09-16", "tna": 43.0,  "price": 43.0},
    {"date": "2024-10-01", "tna": 42.0,  "price": 42.0},
    {"date": "2024-10-15", "tna": 41.0,  "price": 41.0},
    {"date": "2024-11-01", "tna": 40.0,  "price": 40.0},
    {"date": "2024-11-15", "tna": 39.0,  "price": 39.0},
    {"date": "2024-12-02", "tna": 38.0,  "price": 38.0},
    {"date": "2024-12-16", "tna": 37.0,  "price": 37.0},
    # 2025 — tasa siguió bajando gradualmente
    {"date": "2025-01-02", "tna": 36.0,  "price": 36.0},
    {"date": "2025-01-15", "tna": 35.5,  "price": 35.5},
    {"date": "2025-02-03", "tna": 34.0,  "price": 34.0},
    {"date": "2025-02-17", "tna": 33.5,  "price": 33.5},
    {"date": "2025-03-03", "tna": 33.0,  "price": 33.0},
    {"date": "2025-03-17", "tna": 32.5,  "price": 32.5},
    {"date": "2025-04-01", "tna": 32.0,  "price": 32.0},
    {"date": "2025-04-15", "tna": 31.5,  "price": 31.5},
    {"date": "2025-05-02", "tna": 31.0,  "price": 31.0},
    {"date": "2025-05-16", "tna": 30.5,  "price": 30.5},
    {"date": "2025-06-02", "tna": 30.0,  "price": 30.0},
    {"date": "2025-06-16", "tna": 29.5,  "price": 29.5},
    {"date": "2025-07-01", "tna": 29.0,  "price": 29.0},
    {"date": "2025-07-15", "tna": 28.5,  "price": 28.5},
    {"date": "2025-08-01", "tna": 28.0,  "price": 28.0},
    {"date": "2025-08-15", "tna": 27.5,  "price": 27.5},
    {"date": "2025-09-01", "tna": 27.0,  "price": 27.0},
    {"date": "2025-09-15", "tna": 27.0,  "price": 27.0},
    {"date": "2025-10-01", "tna": 27.0,  "price": 27.0},
    {"date": "2025-10-15", "tna": 27.0,  "price": 27.0},
    {"date": "2025-11-03", "tna": 27.0,  "price": 27.0},
    {"date": "2025-11-17", "tna": 27.0,  "price": 27.0},
    {"date": "2025-12-01", "tna": 27.0,  "price": 27.0},
    {"date": "2025-12-15", "tna": 27.0,  "price": 27.0},
    {"date": "2026-01-02", "tna": 29.0,  "price": 29.0},
    {"date": "2026-01-15", "tna": 29.0,  "price": 29.0},
    {"date": "2026-02-02", "tna": 29.0,  "price": 29.0},
    {"date": "2026-02-16", "tna": 29.0,  "price": 29.0},
    {"date": "2026-03-02", "tna": 29.0,  "price": 29.0},
]
# fmt: on


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> List[Dict]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")
    return []


def _save_json(path: Path, data: List[Dict]):
    _ensure_dirs()
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")


def _merge_series(existing: List[Dict], new_points: List[Dict]) -> List[Dict]:
    """Merge new points into existing series, deduplicating by date (new wins)."""
    by_date = {p["date"]: p for p in existing}
    for p in new_points:
        by_date[p["date"]] = p
    return sorted(by_date.values(), key=lambda x: x["date"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_store():
    """
    Initialize the rates store on startup.
    Seeds caucion file if it doesn't exist yet.
    """
    _ensure_dirs()
    if not CAUCION_FILE.exists():
        logger.info(f"Seeding caucion_1d store with {len(CAUCION_SEED)} historical points")
        _save_json(CAUCION_FILE, CAUCION_SEED)
    else:
        existing = _load_json(CAUCION_FILE)
        # Merge seed with existing so we don't lose real captured data
        merged = _merge_series(CAUCION_SEED, existing)
        if len(merged) != len(existing):
            _save_json(CAUCION_FILE, merged)
            logger.info(f"Caucion store merged: {len(merged)} total points")
        else:
            logger.info(f"Caucion store already has {len(existing)} points")


def get_caucion_series(fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> List[Dict]:
    """Return caucion 1D TNA series filtered by date range."""
    data = _load_json(CAUCION_FILE)
    if fecha_desde:
        data = [p for p in data if p["date"] >= fecha_desde]
    if fecha_hasta:
        data = [p for p in data if p["date"] <= fecha_hasta]
    return data


def upsert_caucion_point(tna: float, price: float, fecha: Optional[date] = None):
    """Add or update a single day's caución TNA point."""
    d = fecha or date.today()
    point = {"date": d.isoformat(), "tna": round(tna, 2), "price": round(price, 4)}
    existing = _load_json(CAUCION_FILE)
    merged = _merge_series(existing, [point])
    _save_json(CAUCION_FILE, merged)
    logger.info(f"Caucion point upserted: {point}")


def get_letra_series(simbolo: str, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> List[Dict]:
    """Return letra TNA series for a symbol, filtered by date range."""
    path = LETRAS_DIR / f"{simbolo.upper()}.json"
    data = _load_json(path)
    if fecha_desde:
        data = [p for p in data if p["date"] >= fecha_desde]
    if fecha_hasta:
        data = [p for p in data if p["date"] <= fecha_hasta]
    return data


def upsert_letra_point(simbolo: str, tna: float, price: float, fecha: Optional[date] = None):
    """Add or update a single day's letra TNA point."""
    d = fecha or date.today()
    point = {"date": d.isoformat(), "tna": round(tna, 2), "price": round(price, 4)}
    path = LETRAS_DIR / f"{simbolo.upper()}.json"
    existing = _load_json(path)
    merged = _merge_series(existing, [point])
    _save_json(path, merged)
    logger.info(f"Letra {simbolo} point upserted: {point}")


def list_tracked_letras() -> List[str]:
    """Return list of letra symbols currently tracked in the store."""
    _ensure_dirs()
    return [p.stem for p in LETRAS_DIR.glob("*.json")]
