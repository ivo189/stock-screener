from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WeeklyPrice(BaseModel):
    date: str
    close: float


class StockMetrics(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    index_membership: list[str] = []

    # Price
    current_price: Optional[float] = None
    price_52w_high: Optional[float] = None
    price_52w_low: Optional[float] = None
    pct_above_52w_low: Optional[float] = None

    # Valuation
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    market_cap: Optional[float] = None

    # Income / yield
    dividend_yield: Optional[float] = None  # percentage, e.g. 3.2
    eps_ttm: Optional[float] = None
    eps_cagr_5y: Optional[float] = None  # percentage, e.g. 8.5

    # Risk
    beta: Optional[float] = None
    price_volatility_1y: Optional[float] = None  # annualized

    # History for charts
    weekly_prices: list[WeeklyPrice] = []

    # Meta
    last_updated: Optional[datetime] = None
    data_quality_score: float = 0.0
    quality_score: Optional[float] = None  # composite screener score 0-100


class StockSummary(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    index_membership: list[str] = []
    current_price: Optional[float] = None
    pct_above_52w_low: Optional[float] = None
    trailing_pe: Optional[float] = None
    eps_cagr_5y: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    market_cap: Optional[float] = None
    price_52w_low: Optional[float] = None
    price_52w_high: Optional[float] = None
    data_quality_score: float = 0.0
    quality_score: Optional[float] = None
    passes_filter: bool = False
    last_updated: Optional[datetime] = None
