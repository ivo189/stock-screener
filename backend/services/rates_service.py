"""
Rates comparison service: Caución 1D TNA vs Letras del Tesoro TNA.

Data strategy:
  - Caución: served from persistent store (seeded historically + updated daily by scheduler)
  - Letras: served from persistent store (captured daily via IOL current price + TNA formula)
  - IOL serie historica is NOT used (letras return HTTP 500, caución returns 404)

TNA formulas:
  Caución: already stored as TNA% (captured from IOL current price at market close)
  Letra (discount instrument): TNA = ((100 / precio) ^ (365 / dias_al_vencimiento) - 1) * 100
"""
import logging
import re
from datetime import date, datetime
from typing import Optional, List, Dict

from services.iol_client import get_cotizacion
from services.rates_store import (
    get_caucion_series,
    get_letra_series,
    upsert_caucion_point,
    upsert_letra_point,
)

logger = logging.getLogger(__name__)

# IOL symbol for Caución Bursátil Tomadora 1 día (pesos)
# IOL does NOT expose a historical series for cauciones, so we use current price daily
CAUCION_IOL_SYMBOLS = [
    "CAUCIONES",
    "CAUC1D",
    "CAUCION_1D_TOMA_PESOS",
    "CAUCPESOS1D",
]


# ---------------------------------------------------------------------------
# TNA helpers
# ---------------------------------------------------------------------------

def _tna_from_caucion_price(price: float) -> Optional[float]:
    """
    Convert caución IOL price to TNA%.
    IOL returns different formats:
      - Daily % (e.g. 0.08 = 0.08%/day) → TNA = price * 365
      - Already TNA (e.g. 29.0 = 29% annual) → use directly
    Heuristic: if value < 5, treat as daily %; otherwise as TNA.
    """
    if price is None or price <= 0:
        return None
    if price < 5:
        return round(price * 365, 2)
    return round(float(price), 2)


def _tna_from_letra(precio: float, vencimiento: date, fecha_cotizacion: date) -> Optional[float]:
    """
    Compute TNA for a discount letra.
    TNA = ((100 / precio) ^ (365 / dias) - 1) * 100
    """
    dias = (vencimiento - fecha_cotizacion).days
    if dias <= 0 or precio is None or precio <= 0:
        return None
    try:
        return round(((100.0 / precio) ** (365.0 / dias) - 1) * 100, 2)
    except Exception:
        return None


def _parse_vencimiento(simbolo: str) -> Optional[date]:
    """
    Parse maturity date from BYMA letra symbol.
    Format: [Prefix][DD][MonthCode][YearDigit]
    Examples: S17A6 → 17-Apr-2026, S29Y6 → 29-May-2026, S30J6 → 30-Jun-2026

    Month codes: F=Feb, H=Mar, A=Apr, Y=May, J=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec, G=Jan
    """
    raw = simbolo.upper()
    byma_month = {
        'F': 2, 'H': 3, 'A': 4, 'Y': 5, 'J': 6,
        'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12, 'G': 1,
    }

    # Standard BYMA format: S17A6, S30J6, S29Y6
    m = re.match(r'^[A-Z](\d{2})([FHAYNJQUVXZG])(\d)$', raw)
    if m:
        day = int(m.group(1))
        month = byma_month.get(m.group(2))
        year = 2020 + int(m.group(3))
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # Extended format: S30JN25 (day + 2-letter month abbrev + 2-digit year)
    m2 = re.match(r'^[A-Z](\d{2})([A-Z]{2})(\d{2})$', raw)
    if m2:
        abbr_map = {
            'EN': 1, 'FE': 2, 'MA': 3, 'AB': 4, 'MY': 5, 'JN': 6,
            'JL': 7, 'AG': 8, 'SE': 9, 'OC': 10, 'NO': 11, 'DI': 12,
        }
        month = abbr_map.get(m2.group(2).upper())
        if month:
            try:
                return date(2000 + int(m2.group(3)), month, int(m2.group(1)))
            except ValueError:
                pass

    logger.debug(f"Could not parse vencimiento from symbol '{simbolo}'")
    return None


# ---------------------------------------------------------------------------
# Daily capture (called by scheduler at market close ~17:15 ART)
# ---------------------------------------------------------------------------

async def capture_daily_rates(letras_to_track: Optional[List[str]] = None):
    """
    Capture today's caucion TNA and all tracked letras TNA from IOL.
    Called daily by the scheduler after market close.
    """
    today = date.today()
    errors = []

    # 1. Capture caución current price
    caucion_captured = False
    for symbol in CAUCION_IOL_SYMBOLS:
        try:
            data = await get_cotizacion(symbol)
            price = data.get("ultimoPrecio") or data.get("ultimo")
            if price:
                tna = _tna_from_caucion_price(float(price))
                if tna:
                    upsert_caucion_point(tna=tna, price=float(price), fecha=today)
                    caucion_captured = True
                    logger.info(f"Caucion daily capture: symbol={symbol}, price={price}, TNA={tna}%")
                    break
        except Exception as e:
            logger.debug(f"Caucion symbol '{symbol}' failed: {e}")

    if not caucion_captured:
        errors.append("caucion: no symbol returned data from IOL")
        logger.warning("Could not capture caucion from IOL today — store retains last value")

    # 2. Capture letras
    from services.rates_store import list_tracked_letras
    symbols = list(set((letras_to_track or []) + list_tracked_letras()))

    for simbolo in symbols:
        vencimiento = _parse_vencimiento(simbolo)
        if vencimiento is None:
            logger.warning(f"Skipping letra '{simbolo}': cannot parse vencimiento")
            continue
        if vencimiento <= today:
            logger.info(f"Skipping letra '{simbolo}': already expired ({vencimiento})")
            continue
        try:
            data = await get_cotizacion(simbolo)
            price = data.get("ultimoPrecio") or data.get("ultimo")
            if price:
                tna = _tna_from_letra(float(price), vencimiento, today)
                if tna:
                    upsert_letra_point(simbolo=simbolo, tna=tna, price=float(price), fecha=today)
                    logger.info(f"Letra {simbolo} daily capture: price={price}, TNA={tna}%")
        except Exception as e:
            errors.append(f"{simbolo}: {e}")
            logger.warning(f"Failed to capture letra '{simbolo}': {e}")

    return {"captured_at": today.isoformat(), "errors": errors}


# ---------------------------------------------------------------------------
# Query functions (used by the API router)
# ---------------------------------------------------------------------------

async def get_caucion_history(fecha_desde: str, fecha_hasta: str) -> List[Dict]:
    """Return caucion 1D TNA series from the persistent store."""
    return get_caucion_series(fecha_desde, fecha_hasta)


async def get_letra_history(simbolo: str, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
    """
    Return letra TNA series from the store.
    If the store has no data for this symbol yet, capture today's price on-demand.
    """
    data = get_letra_series(simbolo, fecha_desde, fecha_hasta)
    if not data:
        # On-demand capture: try to get at least today's price
        vencimiento = _parse_vencimiento(simbolo)
        if vencimiento and vencimiento > date.today():
            try:
                cotiz = await get_cotizacion(simbolo)
                price = cotiz.get("ultimoPrecio") or cotiz.get("ultimo")
                if price:
                    tna = _tna_from_letra(float(price), vencimiento, date.today())
                    if tna:
                        upsert_letra_point(simbolo=simbolo, tna=tna, price=float(price))
                        data = get_letra_series(simbolo, fecha_desde, fecha_hasta)
                        logger.info(f"On-demand capture for {simbolo}: TNA={tna}%")
            except Exception as e:
                logger.warning(f"On-demand capture failed for '{simbolo}': {e}")
    return data


async def get_rates_comparison(
    letras: List[str],
    fecha_desde: str,
    fecha_hasta: str,
) -> Dict:
    """
    Combine caucion 1D TNA + multiple letras TNA from the persistent store.
    """
    # Fetch all concurrently
    import asyncio

    caucion_task = get_caucion_history(fecha_desde, fecha_hasta)
    letra_tasks = {s: get_letra_history(s, fecha_desde, fecha_hasta) for s in letras}

    caucion_data = await caucion_task

    letras_response = {}
    for simbolo, task in letra_tasks.items():
        data = await task
        vencimiento = _parse_vencimiento(simbolo)
        letras_response[simbolo] = {
            "data": data,
            "vencimiento": vencimiento.isoformat() if vencimiento else None,
            "error": None if data else "Sin datos aún — se capturará en el próximo cierre de mercado",
        }

    return {
        "caucion_1d": caucion_data,
        "letras": letras_response,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }
