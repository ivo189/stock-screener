"""
Rates comparison service: Caución 1D (tomadora) TNA vs Letras del Tesoro TNA.

Caución TNA formula:
  The IOL historical series for "CAUCIONES" returns a daily closing rate expressed
  as a daily TNA (already annualised by IOL in some endpoints) or as a daily effective
  rate. We normalise everything to TNA (Tasa Nominal Anual, base 365).

  If IOL returns the caución as a daily percentage (e.g. 0.12% per day):
    TNA = tasa_diaria_pct * 365

  If IOL returns it already as TNA (annualised), we use it directly.

Letra TNA formula (discount instrument):
  TNA = ((VN / Precio) ^ (365 / dias_al_vencimiento) - 1) * 100
  where VN = 100 (par value), Precio = closing price, dias = days to maturity.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Any

from services.iol_client import get_serie_historica, get_cotizacion

logger = logging.getLogger(__name__)

# IOL symbol for Caución Bursátil Tomadora 1 día (pesos)
CAUCION_1D_SYMBOL = "CAUCION_1D_TOMA_PESOS"

# Fallback symbol variants IOL uses for cauciones
CAUCION_SYMBOLS_FALLBACK = [
    "CAUCIONES",
    "CAUC1D",
    "CAUCPESOS1D",
]


def _tna_from_caucion_price(price: float, days: int = 1) -> float | None:
    """
    Convert a caución closing price / rate to TNA%.
    IOL returns caución prices in different ways depending on the endpoint:
    - As a daily percentage rate (e.g. 0.12 means 0.12% per day)
    - As an annualised rate already (e.g. 44.0 means 44% TNA)
    We detect which by magnitude: if value < 5 it's a daily rate, otherwise it's already TNA.
    """
    if price is None or price <= 0:
        return None
    if price < 5:
        # Daily rate in percent → annualise
        return round(price * 365, 2)
    # Already TNA
    return round(float(price), 2)


def _tna_from_letra(precio: float, vencimiento: date, fecha_cotizacion: date) -> float | None:
    """
    Compute TNA for a discount letra given its closing price and maturity date.
    TNA = ((100 / precio) ^ (365 / dias) - 1) * 100
    """
    dias = (vencimiento - fecha_cotizacion).days
    if dias <= 0 or precio is None or precio <= 0:
        return None
    try:
        tna = ((100.0 / precio) ** (365.0 / dias) - 1) * 100
        return round(tna, 2)
    except Exception:
        return None


def _parse_vencimiento(simbolo: str) -> date | None:
    """
    Attempt to parse the maturity date from the letra symbol.
    Common formats used by BYMA/IOL:
      S17A6  → 17-Apr-2026  (Sddmmy — day + 1-letter month + 1-digit year)
      S30A6  → 30-Apr-2026
      S29Y6  → 29-May-2026  (Y = May in BYMA convention)
      S30J6  → 30-Jun-2026
      X17A6  → 17-Apr-2026  (X prefix also used)
    Month codes: F=Feb, H=Mar, A=Apr, Y=May, J=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec, G=Jan
    """
    # Strip prefix letters until we hit digits
    s = simbolo.upper().lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    raw = simbolo.upper()

    # Try BYMA short format: [letter][DD][MonthCode][Y]  e.g. S17A6
    byma_month = {
        'F': 2, 'H': 3, 'A': 4, 'Y': 5, 'J': 6,
        'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12, 'G': 1,
    }
    import re
    m = re.match(r'^[A-Z](\d{2})([FHAYNJQUVXZG])(\d)$', raw)
    if m:
        day = int(m.group(1))
        month = byma_month.get(m.group(2))
        year_digit = int(m.group(3))
        year = 2020 + year_digit
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # Try longer format like S30JN25 or similar
    m2 = re.match(r'^[A-Z](\d{2})([A-Z]{2})(\d{2})$', raw)
    if m2:
        month_abbr = m2.group(2).capitalize()
        months = {
            'En': 1, 'Fe': 2, 'Ma': 3, 'Ab': 4, 'My': 5, 'Jn': 6,
            'Jl': 7, 'Ag': 8, 'Se': 9, 'Oc': 10, 'No': 11, 'Di': 12,
            'Ja': 1, 'Ju': 6, 'Au': 8, 'Oc': 10,
        }
        month = months.get(month_abbr)
        if month:
            try:
                return date(2000 + int(m2.group(3)), month, int(m2.group(1)))
            except ValueError:
                pass

    logger.warning(f"Could not parse maturity date from symbol '{simbolo}'")
    return None


def _normalize_series(raw: list[dict], symbol: str, symbol_type: str, vencimiento: date | None) -> list[dict]:
    """
    Convert a raw IOL historical series to a list of {date, tna} points.
    symbol_type: 'caucion' | 'letra'
    """
    result = []
    for item in raw:
        # IOL returns fecha as ISO datetime string
        fecha_str = item.get("fechaHora") or item.get("fecha") or item.get("date") or ""
        if not fecha_str:
            continue
        try:
            fecha = datetime.fromisoformat(fecha_str[:10]).date()
        except ValueError:
            continue

        # Price field: 'ultimo', 'cierre', 'close', 'precio'
        price = (
            item.get("ultimo")
            or item.get("cierre")
            or item.get("ultimoPrecio")
            or item.get("close")
        )
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        if symbol_type == "caucion":
            tna = _tna_from_caucion_price(price)
        else:  # letra
            if vencimiento is None:
                continue
            tna = _tna_from_letra(price, vencimiento, fecha)

        if tna is not None and tna > 0:
            result.append({"date": fecha.isoformat(), "tna": tna, "price": round(price, 4)})

    return sorted(result, key=lambda x: x["date"])


async def get_caucion_history(fecha_desde: str, fecha_hasta: str) -> list[dict]:
    """
    Fetch Caución Tomadora 1D TNA history from IOL.
    Returns list of {date, tna, price}.
    """
    symbols_to_try = [CAUCION_1D_SYMBOL] + CAUCION_SYMBOLS_FALLBACK

    for symbol in symbols_to_try:
        try:
            raw = await get_serie_historica(symbol, fecha_desde, fecha_hasta)
            if raw:
                data = _normalize_series(raw, symbol, "caucion", None)
                if data:
                    logger.info(f"Caución history fetched via symbol '{symbol}': {len(data)} points")
                    return data
        except Exception as e:
            logger.debug(f"Symbol '{symbol}' failed: {e}")

    logger.warning("Could not fetch caución history from any symbol variant")
    return []


async def get_letra_history(simbolo: str, fecha_desde: str, fecha_hasta: str) -> list[dict]:
    """
    Fetch a Letra del Tesoro TNA history from IOL.
    Returns list of {date, tna, price}.
    """
    vencimiento = _parse_vencimiento(simbolo)
    if vencimiento is None:
        logger.warning(f"Could not determine vencimiento for '{simbolo}', TNA will be None")

    try:
        raw = await get_serie_historica(simbolo, fecha_desde, fecha_hasta)
        if not raw:
            return []
        data = _normalize_series(raw, simbolo, "letra", vencimiento)
        logger.info(f"Letra '{simbolo}' history: {len(data)} points, vto={vencimiento}")
        return data
    except Exception as e:
        logger.warning(f"Failed to fetch letra '{simbolo}' history: {e}")
        return []


async def get_rates_comparison(
    letras: list[str],
    fecha_desde: str,
    fecha_hasta: str,
) -> dict:
    """
    Fetch and combine caución 1D TNA + multiple letras TNA into a unified response.

    Returns:
    {
      "caucion_1d": [{"date": "2025-01-15", "tna": 44.5, "price": 0.122}, ...],
      "letras": {
        "S17A6": {"data": [...], "vencimiento": "2026-04-17", "error": null},
        ...
      },
      "fecha_desde": "...",
      "fecha_hasta": "..."
    }
    """
    import asyncio

    # Fetch caucion and all letras concurrently
    caucion_task = get_caucion_history(fecha_desde, fecha_hasta)
    letra_tasks = {s: get_letra_history(s, fecha_desde, fecha_hasta) for s in letras}

    caucion_data = await caucion_task
    letra_results = {}
    for simbolo, task in letra_tasks.items():
        letra_results[simbolo] = await task

    # Build response
    letras_response = {}
    for simbolo, data in letra_results.items():
        vencimiento = _parse_vencimiento(simbolo)
        letras_response[simbolo] = {
            "data": data,
            "vencimiento": vencimiento.isoformat() if vencimiento else None,
            "error": None if data else "Sin datos o símbolo no encontrado en IOL",
        }

    return {
        "caucion_1d": caucion_data,
        "letras": letras_response,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }
