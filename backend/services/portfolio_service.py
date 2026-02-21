import math
from collections import defaultdict
from typing import Optional

from config import (
    DEFAULT_MAX_SECTOR_WEIGHT,
    DEFAULT_MAX_SINGLE_STOCK_WEIGHT,
    MAX_PORTFOLIO_ITERATIONS,
)
from models.portfolio import (
    PortfolioPosition,
    PortfolioRequest,
    PortfolioResponse,
    SectorAllocation,
)
from models.stock import StockMetrics


def _compute_weights_equal(stocks: list[StockMetrics]) -> dict[str, float]:
    n = len(stocks)
    return {s.ticker: 1.0 / n for s in stocks}


def _compute_weights_risk_parity(stocks: list[StockMetrics]) -> dict[str, float]:
    """Inverse volatility weighting. Falls back to equal if volatility unavailable."""
    vols = {}
    for s in stocks:
        v = s.price_volatility_1y
        if v is None or v <= 0:
            v = 0.3  # default 30% annual vol assumption
        vols[s.ticker] = v

    inv_vols = {t: 1.0 / v for t, v in vols.items()}
    total = sum(inv_vols.values())
    return {t: iv / total for t, iv in inv_vols.items()}


def _compute_weights_market_cap(stocks: list[StockMetrics]) -> dict[str, float]:
    """Market cap weighting. Falls back to equal for missing market cap."""
    caps = {}
    for s in stocks:
        caps[s.ticker] = s.market_cap or 1.0
    total = sum(caps.values())
    return {t: c / total for t, c in caps.items()}


def _enforce_constraints(
    weights: dict[str, float],
    stocks: list[StockMetrics],
    max_single: float,
    max_sector: float,
) -> tuple[dict[str, float], list[str]]:
    """Iteratively cap position and sector weights. Returns final weights and warnings."""
    sector_map = {s.ticker: (s.sector or "Unknown") for s in stocks}
    warnings = []

    for iteration in range(MAX_PORTFOLIO_ITERATIONS):
        capped = False

        # Cap single positions
        for ticker in list(weights.keys()):
            if weights[ticker] > max_single:
                weights[ticker] = max_single
                capped = True

        # Re-normalize
        total = sum(weights.values())
        if total > 0:
            weights = {t: w / total for t, w in weights.items()}

        # Cap sectors
        sector_weights: dict[str, float] = defaultdict(float)
        for t, w in weights.items():
            sector_weights[sector_map[t]] += w

        for sector, sw in sector_weights.items():
            if sw > max_sector:
                excess = sw - max_sector
                # Reduce all tickers in this sector proportionally
                sector_tickers = [t for t in weights if sector_map[t] == sector]
                total_sector_w = sum(weights[t] for t in sector_tickers)
                if total_sector_w > 0:
                    for t in sector_tickers:
                        reduction = excess * (weights[t] / total_sector_w)
                        weights[t] = max(0.0, weights[t] - reduction)
                capped = True

        # Re-normalize again
        total = sum(weights.values())
        if total > 0:
            weights = {t: w / total for t, w in weights.items()}

        if not capped:
            break
    else:
        warnings.append(
            "Portfolio constraints could not be fully satisfied. "
            "Some sector or position limits may be slightly exceeded."
        )

    return weights, warnings


def build_portfolio(
    stocks: list[StockMetrics],
    request: PortfolioRequest,
) -> PortfolioResponse:
    warnings = []

    if not stocks:
        return PortfolioResponse(
            positions=[],
            sector_allocations=[],
            portfolio_beta=0.0,
            portfolio_volatility=0.0,
            diversification_score=0.0,
            total_positions=0,
            weighting_method=request.weighting_method,
            warnings=["No stocks provided."],
        )

    # Step 1: Compute initial weights
    method = request.weighting_method
    if method == "risk_parity":
        weights = _compute_weights_risk_parity(stocks)
    elif method == "market_cap":
        weights = _compute_weights_market_cap(stocks)
    else:
        weights = _compute_weights_equal(stocks)
        method = "equal"

    # Step 2: Enforce constraints
    weights, constraint_warnings = _enforce_constraints(
        weights, stocks, request.max_single_stock_weight, request.max_sector_weight
    )
    warnings.extend(constraint_warnings)

    # Step 3: Build positions
    stock_map = {s.ticker: s for s in stocks}
    positions = []
    for ticker, weight in sorted(weights.items(), key=lambda x: -x[1]):
        s = stock_map[ticker]
        target_amount = None
        target_shares = None
        if request.total_capital and s.current_price and s.current_price > 0:
            target_amount = round(weight * request.total_capital, 2)
            target_shares = math.floor(target_amount / s.current_price)

        positions.append(
            PortfolioPosition(
                ticker=ticker,
                name=s.name,
                sector=s.sector or "Unknown",
                target_weight=round(weight, 4),
                target_amount=target_amount,
                target_shares=target_shares,
                current_price=s.current_price,
                beta=s.beta,
                volatility=s.price_volatility_1y,
                quality_score=None,
                pct_above_52w_low=s.pct_above_52w_low,
                dividend_yield=s.dividend_yield,
                trailing_pe=s.trailing_pe,
            )
        )

    # Step 4: Portfolio metrics
    portfolio_beta = 0.0
    portfolio_vol = 0.0
    for p in positions:
        b = p.beta if p.beta is not None else 1.0
        v = p.volatility if p.volatility is not None else 0.3
        portfolio_beta += p.target_weight * b
        portfolio_vol += (p.target_weight * v) ** 2
    portfolio_vol = round(math.sqrt(portfolio_vol), 4)
    portfolio_beta = round(portfolio_beta, 4)

    # Herfindahl-Hirschman Index: 1 = perfectly diversified, ~0 = concentrated
    hhi = sum(w ** 2 for w in weights.values())
    n = len(weights)
    diversification_score = round(1.0 - hhi, 4) if n > 1 else 0.0

    # Step 5: Sector allocations
    sector_tickers: dict[str, list[str]] = defaultdict(list)
    sector_weights: dict[str, float] = defaultdict(float)
    for p in positions:
        sec = p.sector or "Unknown"
        sector_tickers[sec].append(p.ticker)
        sector_weights[sec] += p.target_weight

    sector_allocations = [
        SectorAllocation(
            sector=sec,
            weight=round(sector_weights[sec], 4),
            tickers=sector_tickers[sec],
        )
        for sec in sorted(sector_weights, key=lambda s: -sector_weights[s])
    ]

    return PortfolioResponse(
        positions=positions,
        sector_allocations=sector_allocations,
        portfolio_beta=portfolio_beta,
        portfolio_volatility=portfolio_vol,
        diversification_score=diversification_score,
        total_positions=len(positions),
        weighting_method=method,
        total_capital=request.total_capital,
        warnings=warnings,
    )
