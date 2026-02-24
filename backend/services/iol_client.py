"""
InvertirOnline API HTTP client.
Wraps all API calls with automatic token injection and 401 retry logic.
"""
import logging
from typing import Any

import httpx

from services.iol_auth import get_bearer_token, invalidate_token

logger = logging.getLogger(__name__)

IOL_BASE_URL = "https://api.invertironline.com/api/v2"
IOL_SANDBOX_BASE_URL = "https://api.invertironline.com/api/v2"  # same base; sandbox differs by endpoint/account

# Mercado codes used by IOL
MERCADO_BCBA = "bCBA"  # Buenos Aires Stock Exchange


async def _request(method: str, path: str, **kwargs) -> Any:
    """
    Execute an authenticated request against the IOL API.
    Automatically retries once after re-authenticating on 401.
    """
    for attempt in range(2):
        token = await get_bearer_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(
                method,
                f"{IOL_BASE_URL}{path}",
                headers=headers,
                **kwargs,
            )

        if resp.status_code == 401 and attempt == 0:
            logger.warning("IOL API returned 401 — invalidating token and retrying...")
            invalidate_token()
            continue

        resp.raise_for_status()
        return resp.json()

    raise RuntimeError("IOL API authentication failed after retry")


async def get_cotizacion(simbolo: str, mercado: str = MERCADO_BCBA) -> dict:
    """
    GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion
    Returns current price quote for a bond symbol.
    """
    path = f"/{mercado}/Titulos/{simbolo}/Cotizacion"
    return await _request("GET", path)


async def get_cotizacion_detalle(simbolo: str, mercado: str = MERCADO_BCBA) -> dict:
    """
    GET /api/v2/{mercado}/Titulos/{simbolo}/CotizacionDetalle
    Returns detailed quote (bid, ask, open, close, volume, etc.)
    """
    path = f"/{mercado}/Titulos/{simbolo}/CotizacionDetalle"
    return await _request("GET", path)


async def get_serie_historica(
    simbolo: str,
    fecha_desde: str,
    fecha_hasta: str,
    ajustada: str = "sinAjustar",
    mercado: str = MERCADO_BCBA,
) -> list[dict]:
    """
    GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{fechaDesde}/{fechaHasta}/{ajustada}
    Returns historical price series. Dates in YYYY-MM-DD format.
    ajustada: "sinAjustar" | "ajustada"
    """
    path = f"/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{fecha_desde}/{fecha_hasta}/{ajustada}"
    return await _request("GET", path)


async def place_order(order_payload: dict) -> dict:
    """
    POST /api/v2/operar/Comprar or /api/v2/operar/Vender
    Places a buy or sell order (use sandbox=True to avoid real execution).
    order_payload must include: mercado, simbolo, cantidad, precio, plazo, validez, tipoOrden
    """
    side = order_payload.get("side", "buy").lower()
    path = "/operar/Comprar" if side == "buy" else "/operar/Vender"

    # Remove our internal 'side' key before sending
    payload = {k: v for k, v in order_payload.items() if k != "side"}
    return await _request("POST", path, json=payload)


async def get_portafolio(pais: str = "argentina") -> dict:
    """
    GET /api/v2/portafolio/{pais}
    Returns current portfolio holdings.
    """
    return await _request("GET", f"/portafolio/{pais}")


async def get_estado_cuenta() -> dict:
    """
    GET /api/v2/estadocuenta
    Returns account balances and cash positions.
    """
    return await _request("GET", "/estadocuenta")
