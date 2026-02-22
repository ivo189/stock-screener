from typing import Optional

from config import MIN_DATA_QUALITY_SCORE
from models.screener import ScreenerFilters
from models.stock import StockMetrics, StockSummary


def calculate_quality_score(stock: StockMetrics, filters: ScreenerFilters) -> float:
    """
    Composite quality score 0-100.
    Higher = better opportunity.
    """
    score = 0.0

    # 1. Distance from 52w low (max 30 pts) — closer = better
    if stock.pct_above_52w_low is not None:
        pct = max(0.0, stock.pct_above_52w_low)
        max_pct = filters.max_pct_above_52w_low or 15.0
        proximity_score = max(0.0, 1.0 - pct / max_pct)
        score += proximity_score * 30

    # 2. P/E ratio (max 25 pts) — lower = better, 0 PE gets 0 pts
    if stock.trailing_pe and stock.trailing_pe > 0:
        max_pe = filters.max_trailing_pe or 20.0
        pe_score = max(0.0, 1.0 - (stock.trailing_pe / max_pe))
        score += pe_score * 25

    # 3. EPS CAGR (max 25 pts) — higher = better (capped at 30%)
    if stock.eps_cagr_5y is not None:
        cagr_score = min(1.0, max(0.0, stock.eps_cagr_5y / 30.0))
        score += cagr_score * 25

    # 4. Dividend yield (max 20 pts) — higher = better (capped at 8%)
    if stock.dividend_yield is not None and stock.dividend_yield > 0:
        div_score = min(1.0, stock.dividend_yield / 8.0)
        score += div_score * 20

    return round(score, 2)


def _passes_filter(stock: StockMetrics, filters: ScreenerFilters) -> bool:
    # Data quality gate
    if stock.data_quality_score < MIN_DATA_QUALITY_SCORE:
        return False

    # Must have a price
    if stock.current_price is None or stock.current_price <= 0:
        return False

    # 1. Near 52-week low
    if stock.pct_above_52w_low is None:
        return False
    if stock.pct_above_52w_low > filters.max_pct_above_52w_low:
        return False

    # Optional: MA200d filter
    if filters.max_pct_vs_ma200d is not None and stock.pct_vs_ma200d is not None:
        if stock.pct_vs_ma200d > filters.max_pct_vs_ma200d:
            return False

    # Optional: MA30w filter
    if filters.max_pct_vs_ma30w is not None and stock.pct_vs_ma30w is not None:
        if stock.pct_vs_ma30w > filters.max_pct_vs_ma30w:
            return False

    # 2. Low P/E
    if stock.trailing_pe is None or stock.trailing_pe <= 0:
        return False
    if stock.trailing_pe > filters.max_trailing_pe:
        return False

    # 3. Growth OR income (configurable)
    has_eps = stock.eps_cagr_5y is not None and stock.eps_cagr_5y >= filters.min_eps_cagr_5y
    has_div = stock.dividend_yield is not None and stock.dividend_yield >= filters.min_dividend_yield

    if filters.require_both_income_filters:
        if not (has_eps and has_div):
            return False
    else:
        if not (has_eps or has_div):
            return False

    return True


def apply_filters(
    stocks: list[StockMetrics],
    filters: ScreenerFilters,
) -> list[StockSummary]:
    results = []
    for stock in stocks:
        # Filter by universe
        stock_indices = set(stock.index_membership)
        if not stock_indices.intersection(set(filters.universe)):
            continue

        passes = _passes_filter(stock, filters)
        quality = calculate_quality_score(stock, filters)

        summary = StockSummary(
            ticker=stock.ticker,
            name=stock.name,
            sector=stock.sector,
            index_membership=stock.index_membership,
            current_price=stock.current_price,
            pct_above_52w_low=stock.pct_above_52w_low,
            trailing_pe=stock.trailing_pe,
            eps_cagr_5y=stock.eps_cagr_5y,
            dividend_yield=stock.dividend_yield,
            beta=stock.beta,
            market_cap=stock.market_cap,
            price_52w_low=stock.price_52w_low,
            price_52w_high=stock.price_52w_high,
            ma_200d=stock.ma_200d,
            ma_30w=stock.ma_30w,
            pct_vs_ma200d=stock.pct_vs_ma200d,
            pct_vs_ma30w=stock.pct_vs_ma30w,
            data_quality_score=stock.data_quality_score,
            quality_score=quality,
            passes_filter=passes,
            last_updated=stock.last_updated,
        )
        results.append(summary)

    # Sort: passing stocks first (by quality desc), then non-passing
    results.sort(key=lambda s: (not s.passes_filter, -(s.quality_score or 0)))
    return results
