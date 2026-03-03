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


def _tna_from_letra(precio: float, vencimiento: date, fecha_cotizacion: date,
                    cierre_anterior: Optional[float] = None) -> Optional[float]:
    """
    Compute TNA for a LECAP (Letra Capitalizable del Tesoro).

    LECAPs are capitalising instruments — they accrue interest daily and at maturity
    pay VN * (1 + tasa_emision/365)^plazo_total. Their market price already reflects
    accrued capitalisation and is quoted > 100 as they approach maturity.

    For a LECAP, the implied TNA is derived from the daily price change (rendimiento
    incremental), annualised to 365 days. This is the standard market convention:

      variacion_diaria = (precio_hoy / precio_ayer) - 1
      TNA = variacion_diaria * 365 * 100

    When we don't have yesterday's price (first capture), we fall back to estimating
    TNA from the price relative to par (100) extrapolating at constant rate:
      days_since_approx_par: estimated as 30 days back from the price exceeding 100
      TNA = ((precio / 100) ^ (365 / dias_desde_emision) - 1) * 100
    This is an approximation valid only for first-day captures.
    """
    dias_al_vto = (vencimiento - fecha_cotizacion).days
    if dias_al_vto <= 0 or precio is None or precio <= 0:
        return None

    try:
        # Primary: use daily price change if we have yesterday's close
        if cierre_anterior and cierre_anterior > 0 and abs(precio - cierre_anterior) > 0.001:
            variacion = (precio / cierre_anterior) - 1.0
            tna = round(variacion * 365 * 100, 2)
            # Sanity check: TNA should be between 0% and 200%
            if 0 < tna < 200:
                return tna

        # Fallback: for first capture, estimate TNA from price vs par extrapolated
        # Assume the letra was issued ~(total_days - dias_al_vto) days ago at 100
        # We can approximate total life as current days_to_maturity + days_accrued
        # where days_accrued is estimated from how far above 100 the price is.
        if precio <= 100:
            # Standard discount: TNA = ((100/precio)^(365/dias) - 1) * 100
            return round(((100.0 / precio) ** (365.0 / dias_al_vto) - 1) * 100, 2)

        # Price > 100 (LECAP over par): estimate TNA from price growth rate
        # Assuming it started at 100 and has been growing at constant TNA:
        # precio = 100 * (1 + TNA/365)^dias_accrued
        # We don't know dias_accrued exactly — use a proxy: assume 30-day emission window
        # and iterate to find TNA that gives current price at current point in lifecycle
        # Simple: use the annualised growth from 100 to precio over estimated accrual period
        # Accrual estimation: if price is ~106 and dias_al_vto ~45, total life ~180d typical
        # → dias_accrued ≈ 180 - 45 = 135
        dias_accrued_estimate = max(30, 180 - dias_al_vto)
        tna_estimated = round(((precio / 100.0) ** (365.0 / dias_accrued_estimate) - 1) * 100, 2)
        if 0 < tna_estimated < 200:
            return tna_estimated

    except Exception:
        pass
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
            cierre_anterior = data.get("cierreAnterior")
            if price:
                tna = _tna_from_letra(
                    float(price), vencimiento, today,
                    cierre_anterior=float(cierre_anterior) if cierre_anterior else None,
                )
                if tna:
                    upsert_letra_point(simbolo=simbolo, tna=tna, price=float(price), fecha=today)
                    logger.info(f"Letra {simbolo} daily capture: price={price}, cierre_ant={cierre_anterior}, TNA={tna}%")
                else:
                    logger.warning(f"Letra {simbolo}: could not compute TNA (price={price}, vto={vencimiento})")
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
                cierre_anterior = cotiz.get("cierreAnterior")
                if price:
                    tna = _tna_from_letra(
                        float(price), vencimiento, date.today(),
                        cierre_anterior=float(cierre_anterior) if cierre_anterior else None,
                    )
                    if tna:
                        upsert_letra_point(simbolo=simbolo, tna=tna, price=float(price))
                        data = get_letra_series(simbolo, fecha_desde, fecha_hasta)
                        logger.info(f"On-demand capture for {simbolo}: price={price}, TNA={tna}%")
                    else:
                        logger.warning(f"On-demand {simbolo}: TNA could not be computed (price={price})")
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
