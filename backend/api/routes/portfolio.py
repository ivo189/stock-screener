from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from core.cache import stock_cache
from models.portfolio import PortfolioRequest, PortfolioResponse
from services.portfolio_service import build_portfolio
from services.monte_carlo import run_monte_carlo, run_bootstrap, compute_portfolio_weekly_returns

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


@router.post("/monte-carlo")
async def portfolio_monte_carlo(request: PortfolioRequest, n_weeks: int = Query(default=52, ge=4, le=260)):
    """Run Monte Carlo simulation on a portfolio built from screened stocks."""
    if len(request.tickers) < 2:
        raise HTTPException(status_code=400, detail="At least 2 tickers required.")

    stocks, missing = _get_stocks_for_tickers(request.tickers)
    if not stocks:
        raise HTTPException(status_code=404, detail="No tickers found in cache.")

    # Build portfolio to get weights
    portfolio = build_portfolio(stocks, request)

    # Build positions with weekly price data
    stock_map = {s.ticker: s for s in stocks}
    positions_data = []
    for pos in portfolio.positions:
        s = stock_map.get(pos.ticker)
        if s:
            # Prefer 5y history for better return estimation; fall back to 1y
            prices = s.weekly_prices_5y if s.weekly_prices_5y else s.weekly_prices
            if prices:
                positions_data.append({
                    "ticker": pos.ticker,
                    "weight": pos.target_weight,
                    "weekly_prices": [{"date": p.date, "close": p.close} for p in prices],
                    "dividend_yield": s.dividend_yield or 0.0,  # annual %, e.g. 2.5
                })

    weekly_returns = compute_portfolio_weekly_returns(positions_data)

    capital = request.total_capital or 10000.0
    mc_result = run_monte_carlo(weekly_returns, capital, n_weeks=n_weeks)
    bs_result = run_bootstrap(weekly_returns, capital, n_weeks=n_weeks)

    return {
        "monte_carlo": mc_result,
        "bootstrap": bs_result,
        "portfolio_positions": len(portfolio.positions),
        "missing_tickers": missing,
        # Keep top-level fields for backward compat (use MC as primary)
        "weeks": mc_result.get("weeks", []),
        "paths": mc_result.get("paths", {}),
        "initial_capital": capital,
        "summary": mc_result.get("summary", {}),
    }
