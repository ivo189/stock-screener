import asyncio

from fastapi import APIRouter, HTTPException, Query

from services import options_service as svc

router = APIRouter(prefix="/api/options", tags=["options"])


@router.get("/scan")
async def scan(
    universe: list[str] = Query(default=["SP500", "NDX"]),
    high_ref: str = Query(default="ath", pattern="^(ath|52w|26w|13w)$"),
    max_dist_pct: float = Query(default=8.0, ge=0, le=50),
    min_vol_pct: float = Query(default=30.0, ge=0),
    min_traded_musd: float = Query(default=300.0, ge=0),
    top: int = Query(default=30, ge=1, le=100),
    force: bool = False,
):
    """Subyacentes cerca de un máximo con vol realizada alta (rankeados por score)."""
    rows = await asyncio.to_thread(
        svc.scan_underlyings, universe, high_ref, max_dist_pct, min_vol_pct, min_traded_musd, top, force
    )
    return {"count": len(rows), "results": rows}


@router.get("/ratio-spreads/{ticker}")
async def ratio_spreads(
    ticker: str,
    x: int = Query(default=1, ge=1, le=10),
    y: int = Query(default=3, ge=2, le=20),
    min_dte: int = Query(default=14, ge=0),
    max_dte: int = Query(default=45, ge=1),
    min_credit: float = Query(default=0.0, description="Crédito neto mínimo por acción"),
    max_otm_long_pct: float = Query(default=5.0, ge=0),
    max_otm_short_pct: float = Query(default=25.0, ge=0),
    min_open_interest: int = Query(default=50, ge=0),
    max_rel_spread: float = Query(default=0.35, gt=0),
    top: int = Query(default=25, ge=1, le=100),
):
    """Combinaciones X:Y de call ratio spread a crédito para un subyacente."""
    try:
        return await asyncio.to_thread(
            svc.find_ratio_spreads, ticker.upper(), x, y, min_dte, max_dte, min_credit,
            max_otm_long_pct, max_otm_short_pct, min_open_interest, max_rel_spread, top,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
