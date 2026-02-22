from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from models.stock import StockSummary


class ScreenerFilters(BaseModel):
    universe: list[str] = ["SP500", "DJIA"]
    max_pct_above_52w_low: float = Field(default=15.0, ge=0, le=100)
    max_trailing_pe: float = Field(default=20.0, ge=0)
    min_eps_cagr_5y: float = Field(default=5.0)
    min_dividend_yield: float = Field(default=2.0, ge=0)
    require_both_income_filters: bool = False
    max_pct_vs_ma200d: Optional[float] = Field(default=None)   # e.g. -10 means price must be >10% below MA200
    max_pct_vs_ma30w: Optional[float] = Field(default=None)    # e.g. -5 means price must be >5% below MA30w


class ScreenerResponse(BaseModel):
    filters_applied: ScreenerFilters
    total_universe_count: int
    passed_count: int
    results: list[StockSummary]
    cache_age_seconds: Optional[float] = None
    generated_at: datetime
