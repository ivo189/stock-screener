from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from core.cache import stock_cache
from models.portfolio import PortfolioRequest, PortfolioResponse
from services.portfolio_service import build_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _get_stocks_for_tickers(tickers: list[str]):
    stocks = []
    missing = []
    for ticker in tickers:
        s = stock_cache.get(ticker.upper())
        if s:
            stocks.append(s)
        else:
            missing.append(ticker)
    return stocks, missing


@router.post("", response_model=PortfolioResponse)
async def build_portfolio_endpoint(request: PortfolioRequest):
    if not request.tickers:
        raise HTTPException(status_code=400, detail="No tickers provided.")
    if len(request.tickers) < 2:
        raise HTTPException(status_code=400, detail="At least 2 tickers are required for a portfolio.")

    stocks, missing = _get_stocks_for_tickers(request.tickers)

    if not stocks:
        raise HTTPException(status_code=404, detail="None of the provided tickers found in cache.")

    result = build_portfolio(stocks, request)
    if missing:
        result.warnings.append(f"Tickers not found in cache (excluded): {', '.join(missing)}")
    return result


@router.get("/preview", response_model=PortfolioResponse)
async def preview_portfolio(
    tickers: list[str] = Query(),
    capital: Optional[float] = Query(default=None),
    method: str = Query(default="risk_parity"),
    max_sector_weight: float = Query(default=0.30),
    max_single_stock_weight: float = Query(default=0.15),
):
    if len(tickers) < 2:
        raise HTTPException(status_code=400, detail="At least 2 tickers required.")

    stocks, missing = _get_stocks_for_tickers(tickers)
    if not stocks:
        raise HTTPException(status_code=404, detail="No tickers found in cache.")

    request = PortfolioRequest(
        tickers=tickers,
        total_capital=capital,
        max_sector_weight=max_sector_weight,
        max_single_stock_weight=max_single_stock_weight,
        weighting_method=method,
    )
    result = build_portfolio(stocks, request)
    if missing:
        result.warnings.append(f"Tickers not found in cache (excluded): {', '.join(missing)}")
    return result
