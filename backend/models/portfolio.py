from typing import Optional
from pydantic import BaseModel, Field


class PortfolioRequest(BaseModel):
    tickers: list[str]
    total_capital: Optional[float] = None
    max_sector_weight: float = Field(default=0.30, ge=0.1, le=1.0)
    max_single_stock_weight: float = Field(default=0.15, ge=0.01, le=1.0)
    weighting_method: str = "risk_parity"  # "equal" | "risk_parity" | "market_cap"


class PortfolioPosition(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    target_weight: float
    target_amount: Optional[float] = None
    target_shares: Optional[int] = None
    current_price: Optional[float] = None
    beta: Optional[float] = None
    volatility: Optional[float] = None
    quality_score: Optional[float] = None
    pct_above_52w_low: Optional[float] = None
    dividend_yield: Optional[float] = None
    trailing_pe: Optional[float] = None


class SectorAllocation(BaseModel):
    sector: str
    weight: float
    tickers: list[str]


class PortfolioResponse(BaseModel):
    positions: list[PortfolioPosition]
    sector_allocations: list[SectorAllocation]
    portfolio_beta: float
    portfolio_volatility: float
    diversification_score: float
    total_positions: int
    weighting_method: str
    total_capital: Optional[float] = None
    warnings: list[str] = []
