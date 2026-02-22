from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from core.cache import stock_cache
from core.scheduler import is_refresh_running, run_full_refresh
from models.screener import ScreenerFilters, ScreenerResponse
from services.screener_service import apply_filters

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("", response_model=ScreenerResponse)
async def run_screener(
    universe: list[str] = Query(default=["SP500", "DJIA"]),
    max_pct_above_52w_low: float = Query(default=15.0, ge=0, le=100),
    max_trailing_pe: float = Query(default=20.0, ge=0),
    min_eps_cagr_5y: float = Query(default=5.0),
    min_dividend_yield: float = Query(default=2.0, ge=0),
    require_both: bool = Query(default=False),
    max_pct_vs_ma200d: Optional[float] = Query(default=None),
    max_pct_vs_ma30w: Optional[float] = Query(default=None),
):
    stocks = stock_cache.get_all()

    filters = ScreenerFilters(
        universe=universe,
        max_pct_above_52w_low=max_pct_above_52w_low,
        max_trailing_pe=max_trailing_pe,
        min_eps_cagr_5y=min_eps_cagr_5y,
        min_dividend_yield=min_dividend_yield,
        require_both_income_filters=require_both,
        max_pct_vs_ma200d=max_pct_vs_ma200d,
        max_pct_vs_ma30w=max_pct_vs_ma30w,
    )

    results = apply_filters(stocks, filters)
    passed = [r for r in results if r.passes_filter]

    return ScreenerResponse(
        filters_applied=filters,
        total_universe_count=len(stocks),
        passed_count=len(passed),
        results=results,
        cache_age_seconds=stock_cache.cache_age_seconds(),
        generated_at=datetime.utcnow(),
    )


def _get_next_refresh_utc() -> datetime:
    """Calculate the next scheduled refresh time (22:30 UTC, Mon-Fri)."""
    from config import REFRESH_HOUR_UTC, REFRESH_MINUTE_UTC
    now = datetime.utcnow()
    target = now.replace(hour=REFRESH_HOUR_UTC, minute=REFRESH_MINUTE_UTC, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    # Skip weekends (5=Sat, 6=Sun)
    while target.weekday() >= 5:
        target += timedelta(days=1)
    return target


@router.get("/universe")
async def get_universe_stats():
    stocks = stock_cache.get_all()
    sectors: dict[str, int] = {}
    for s in stocks:
        sec = s.sector or "Unknown"
        sectors[sec] = sectors.get(sec, 0) + 1

    last_updated = stock_cache._last_batch_update

    return {
        "total_tickers": len(stocks),
        "sectors": sectors,
        "cache_age_seconds": stock_cache.cache_age_seconds(),
        "is_stale": stock_cache.is_stale(),
        "refresh_running": is_refresh_running(),
        "last_updated_at": last_updated.isoformat() if last_updated else None,
        "next_refresh_at": _get_next_refresh_utc().isoformat(),
    }


@router.post("/refresh", status_code=202)
async def trigger_refresh(background_tasks: BackgroundTasks):
    if is_refresh_running():
        raise HTTPException(status_code=409, detail="Refresh already in progress.")
    background_tasks.add_task(run_full_refresh)
    return {"message": "Data refresh triggered. This will take several minutes."}
