from fastapi import APIRouter, HTTPException

from core.cache import stock_cache
from models.stock import StockMetrics
from services.data_fetcher import fetch_stock_metrics
from config import DJIA_TICKERS

router = APIRouter(prefix="/api/stock", tags=["stocks"])


@router.get("/{ticker}", response_model=StockMetrics)
async def get_stock_detail(ticker: str):
    ticker = ticker.upper()
    cached = stock_cache.get(ticker)
    if cached:
        return cached

    # Live fetch if not in cache (single ticker, acceptable latency)
    djia_set = set(DJIA_TICKERS)
    try:
        metrics = fetch_stock_metrics(ticker, djia_set)
        if metrics.current_price is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found or no data available.")
        stock_cache.set(ticker, metrics)
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/price-history")
async def get_price_history(ticker: str):
    ticker = ticker.upper()
    cached = stock_cache.get(ticker)
    if cached and cached.weekly_prices:
        return {"ticker": ticker, "prices": [p.model_dump() for p in cached.weekly_prices]}

    raise HTTPException(status_code=404, detail=f"No price history for '{ticker}'. Trigger a refresh first.")
