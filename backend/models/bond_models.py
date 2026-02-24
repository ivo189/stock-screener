"""
Pydantic models for the bond arbitrage monitor module.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Bond pair configuration
# ---------------------------------------------------------------------------

class BondPairConfig(BaseModel):
    """Definition of a ley-local vs ley-NY bond pair to monitor."""
    id: str                     # e.g. "AL30_GD30"
    label: str                  # e.g. "AL30 / GD30"
    local_symbol: str           # IOL symbol, ley local, e.g. "AL30D"
    ny_symbol: str              # IOL symbol, ley NY, e.g. "GD30D"
    description: str = ""


# ---------------------------------------------------------------------------
# Raw quote snapshot from IOL
# ---------------------------------------------------------------------------

class BondQuote(BaseModel):
    """Single price snapshot for one bond."""
    symbol: str
    price: float                # ultimo precio (last trade price)
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    fetched_at: datetime


# ---------------------------------------------------------------------------
# Commission / cost model
# ---------------------------------------------------------------------------

class CommissionInfo(BaseModel):
    """
    Computed commission costs for a round-trip arbitrage trade.
    roundtrip_cost_pct = total end-to-end cost (configurable via IOL_ROUNDTRIP_COMMISSION).
    """
    roundtrip_cost_pct: float   # total round-trip cost as % (e.g. 0.5)
    gross_spread_pct: float     # |ratio - mean| / mean  (as %)
    net_spread_pct: float       # gross_spread_pct - roundtrip_cost_pct
    is_profitable: bool         # net_spread_pct > 0
    breakeven_ratio: float      # ratio level at which trade breaks even


# ---------------------------------------------------------------------------
# Computed ratio snapshot
# ---------------------------------------------------------------------------

class RatioSnapshot(BaseModel):
    """Ratio = local_price / ny_price at a point in time."""
    pair_id: str
    timestamp: datetime
    local_price: float
    ny_price: float
    ratio: float                # local / ny


# ---------------------------------------------------------------------------
# Statistical analysis over the ratio series
# ---------------------------------------------------------------------------

class RatioStats(BaseModel):
    """Rolling statistics for anomaly detection."""
    mean: float
    std: float
    z_score: float              # (current_ratio - mean) / std
    upper_band: float           # mean + 2*std  (Bollinger upper)
    lower_band: float           # mean - 2*std  (Bollinger lower)
    upper_band_1sigma: float    # mean + 1*std
    lower_band_1sigma: float    # mean - 1*std
    window_size: int            # number of observations used


# ---------------------------------------------------------------------------
# Alert / opportunity
# ---------------------------------------------------------------------------

class ArbitrageAlert(BaseModel):
    """Fired when ratio z-score exceeds the threshold AND net spread > 0."""
    pair_id: str
    pair_label: str
    timestamp: datetime
    ratio: float
    z_score: float
    direction: str              # "LOCAL_CHEAP" | "NY_CHEAP"
    description: str            # human-readable opportunity description
    commission: Optional[CommissionInfo] = None  # P&L breakdown


# ---------------------------------------------------------------------------
# Full state for one pair (returned by the API)
# ---------------------------------------------------------------------------

class BondPairState(BaseModel):
    """Complete current state of one monitored bond pair."""
    config: BondPairConfig
    latest: Optional[RatioSnapshot] = None
    stats: Optional[RatioStats] = None
    alert: Optional[ArbitrageAlert] = None
    commission: Optional[CommissionInfo] = None  # always-present cost info
    history: list[RatioSnapshot] = []
    last_fetch_error: Optional[str] = None
    eod_signal: bool = False    # True when market is about to close
    eod_action: str = "none"    # "hold" | "close" | "none"
                                # hold  = spread persists, keep position overnight
                                # close = spread converged, safe to exit
                                # none  = EOD window not active


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class BondsStatusResponse(BaseModel):
    """Overall monitor status returned by GET /api/bonds/status."""
    pairs: list[BondPairState]
    last_refresh_at: Optional[datetime] = None
    next_refresh_at: Optional[datetime] = None
    refresh_running: bool = False
    iol_authenticated: bool = False
    market_open: bool = False
    eod_signal: bool = False        # global EOD window active flag
    commission_rate: float = 0.005  # total round-trip cost


class BondHistoryResponse(BaseModel):
    """Historical ratio series for a pair, returned by GET /api/bonds/{pair_id}/history."""
    pair_id: str
    pair_label: str
    history: list[RatioSnapshot]
    stats: Optional[RatioStats] = None


# ---------------------------------------------------------------------------
# Order request/response (sandbox & live)
# ---------------------------------------------------------------------------

class BondOrderRequest(BaseModel):
    """Place a buy/sell order on a bond."""
    pair_id: str
    symbol: str                 # exact IOL symbol to trade
    side: str                   # "buy" | "sell"
    quantity: int               # number of VNs (valor nominal)
    price: float                # limit price
    plazo: str = "t2"           # settlement: "t0", "t1", "t2"
    sandbox: bool = True        # True = use sandbox account


class BondOrderResponse(BaseModel):
    """Result of a placed order."""
    success: bool
    order_id: Optional[str] = None
    message: str
    sandbox: bool
    raw_response: Optional[dict] = None


# ---------------------------------------------------------------------------
# Order log entry (persisted)
# ---------------------------------------------------------------------------

class OrderLogEntry(BaseModel):
    """Single executed order, persisted to disk for the operations log."""
    id: str                         # UUID
    timestamp: datetime
    pair_id: str
    pair_label: str
    symbol: str
    side: str                       # "buy" | "sell"
    quantity: int
    price: float
    plazo: str
    sandbox: bool
    success: bool
    order_id: Optional[str] = None
    message: str


class OrderLogResponse(BaseModel):
    """List of executed orders, newest first."""
    entries: list[OrderLogEntry]
    total: int
