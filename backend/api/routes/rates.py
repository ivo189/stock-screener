"""
Tasas ARS — REST API routes.

Endpoints:
  GET  /api/rates/history   — Caución 1D TNA + Letras TNA historical series
  GET  /api/rates/letras    — List available letra symbols (BYMA conventions)
"""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.rates_service import get_rates_comparison, _parse_vencimiento

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rates", tags=["rates"])


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic response models
# ──────────────────────────────────────────────────────────────────────────────

class RatePoint(BaseModel):
    date: str       # ISO date string: "2025-01-15"
    tna: float      # Tasa Nominal Anual (%)
    price: float    # Raw closing price from IOL


class LetraResult(BaseModel):
    data: list[RatePoint]
    vencimiento: str | None     # ISO date string or null
    error: str | None           # null if OK, message if failed


class RatesHistoryResponse(BaseModel):
    caucion_1d: list[RatePoint]
    letras: dict[str, LetraResult]
    fecha_desde: str
    fecha_hasta: str


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _default_dates() -> tuple[str, str]:
    """Return (fecha_desde, fecha_hasta) defaulting to last 3 months."""
    today = date.today()
    desde = today - timedelta(days=90)
    return desde.isoformat(), today.isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=RatesHistoryResponse)
async def get_rates_history(
    letras: list[str] = Query(
        default=[],
        description="Lista de símbolos de Letras del Tesoro, ej: S17A6,S30A6,S29Y6",
    ),
    fecha_desde: str = Query(
        default=None,
        description="Fecha inicio ISO (YYYY-MM-DD). Default: 90 días atrás.",
    ),
    fecha_hasta: str = Query(
        default=None,
        description="Fecha fin ISO (YYYY-MM-DD). Default: hoy.",
    ),
):
    """
    Fetch Caución Bursátil Tomadora 1D TNA + optional Letras del Tesoro TNA series.

    - **letras**: symbols like S17A6, S30A6, S29Y6. Leave empty for caución-only.
    - **fecha_desde** / **fecha_hasta**: ISO date strings. Defaults to last 90 days.

    Returns unified time-series data suitable for charting.
    """
    # Apply defaults
    default_desde, default_hasta = _default_dates()
    fd = fecha_desde or default_desde
    fh = fecha_hasta or default_hasta

    # Basic validation
    try:
        d_from = date.fromisoformat(fd)
        d_to = date.fromisoformat(fh)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fechas deben ser formato ISO YYYY-MM-DD")

    if d_from > d_to:
        raise HTTPException(status_code=422, detail="fecha_desde debe ser anterior a fecha_hasta")

    if (d_to - d_from).days > 730:
        raise HTTPException(status_code=422, detail="Rango máximo de consulta: 2 años (730 días)")

    # Clamp upper bound to today
    today = date.today()
    if d_to > today:
        d_to = today
        fh = today.isoformat()

    # Cap letras list
    if len(letras) > 10:
        raise HTTPException(status_code=422, detail="Máximo 10 letras por consulta")

    logger.info(
        f"rates/history request: letras={letras}, desde={fd}, hasta={fh}"
    )

    try:
        result = await get_rates_comparison(letras, fd, fh)
    except Exception as e:
        logger.error(f"rates/history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos de IOL: {e}")

    return result


@router.get("/letras/parse")
async def parse_letra_symbol(simbolo: str = Query(..., description="Símbolo BYMA, ej: S17A6")):
    """
    Utility endpoint: parse the maturity date from a letra BYMA symbol.
    Returns vencimiento ISO date or null if it could not be determined.
    """
    vencimiento = _parse_vencimiento(simbolo)
    return {
        "simbolo": simbolo,
        "vencimiento": vencimiento.isoformat() if vencimiento else None,
        "parsed": vencimiento is not None,
    }
