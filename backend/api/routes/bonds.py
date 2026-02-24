"""
Bond arbitrage monitor — REST API routes.

Endpoints:
  GET  /api/bonds/status            — full status: all pairs, latest ratios, alerts
  POST /api/bonds/refresh           — trigger immediate data refresh
  GET  /api/bonds/{pair_id}/history — historical ratio series for one pair
  POST /api/bonds/order             — place a bond order (sandbox by default)
  GET  /api/bonds/paper-trades      — paper trade log + stats
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query

from models.bond_models import (
    BondsStatusResponse,
    BondHistoryResponse,
    BondOrderRequest,
    BondOrderResponse,
    OrderLogResponse,
    PaperTradeResponse,
)
from services.bond_service import bond_monitor, execute_order, get_order_log, get_paper_trades

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bonds", tags=["bonds"])


@router.get("/status", response_model=BondsStatusResponse)
async def get_bonds_status():
    """
    Return the current state of all monitored bond pairs.
    Includes latest ratio, Bollinger stats, and any active alerts.
    """
    return bond_monitor.get_status()


@router.post("/refresh")
async def trigger_bond_refresh():
    """
    Manually trigger an immediate fetch of all bond pairs from IOL.
    Returns immediately; refresh runs in the background.
    """
    if bond_monitor.is_running():
        return {"status": "already_running", "message": "Refresh already in progress."}
    asyncio.create_task(bond_monitor.refresh_all())
    return {"status": "started", "message": "Bond data refresh started."}


@router.get("/{pair_id}/history", response_model=BondHistoryResponse)
async def get_pair_history(
    pair_id: str,
    limit: int = Query(default=1500, ge=1, le=1500, description="Max history points (~14 trading days)"),
):
    """
    Return the historical ratio series for a single bond pair with rolling Bollinger stats.
    Each point includes mean, ±1σ, ±2σ and z_score computed over the rolling window.
    """
    try:
        return bond_monitor.get_pair_history(pair_id, limit=limit)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Bond pair '{pair_id}' not found.")


@router.get("/orders", response_model=OrderLogResponse)
async def get_orders(
    limit: int = Query(default=50, ge=1, le=200, description="Max number of log entries"),
):
    """Return the order log (newest first), capped at `limit` entries."""
    return get_order_log(limit=limit)


@router.post("/order", response_model=BondOrderResponse)
async def place_bond_order(req: BondOrderRequest):
    """
    Place a buy or sell order on a bond symbol via IOL API.
    By default operates in sandbox mode (req.sandbox=True).
    Set req.sandbox=False to place a real order — use with caution.
    """
    if not req.sandbox:
        logger.warning(
            f"LIVE ORDER requested: {req.side} {req.quantity} {req.symbol} @ {req.price}"
        )
    result = await execute_order(req)
    if not result.success:
        # Return 200 with success=False rather than 500 so the frontend
        # can display the error message from the IOL API.
        pass
    return result


@router.get("/paper-trades", response_model=PaperTradeResponse)
async def get_paper_trade_log(
    limit: int = Query(default=100, ge=1, le=500, description="Max closed trades to return"),
):
    """
    Return the paper trading log: open positions + closed trades with P&L.
    Trades are opened automatically when z-score >= threshold and closed at ±0.5σ.
    """
    return get_paper_trades(limit=limit)
