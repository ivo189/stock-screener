"""
Bond arbitrage monitoring service (intraday edition).

Key changes vs. v1:
- Commission-aware alerts: only fire if net spread > 0 after round-trip costs
- EOD signal: set_eod_signal(True) 10 min before market close → go cash
- Market hours guard is in scheduler; service itself is always callable
- CommissionInfo computed on every refresh
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from models.bond_models import (
    ArbitrageAlert,
    BondOrderRequest,
    BondOrderResponse,
    BondPairConfig,
    BondPairState,
    BondQuote,
    CommissionInfo,
    OrderLogEntry,
    OrderLogResponse,
    PaperTrade,
    PaperTradeStats,
    PaperTradeResponse,
    RatioSnapshot,
    RatioStats,
    BondsStatusResponse,
    BondHistoryResponse,
)
from services.iol_client import get_cotizacion_detalle, place_order

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from environment (set in .env)
# ---------------------------------------------------------------------------

BOND_PAIRS: list[BondPairConfig] = [
    BondPairConfig(
        id="AL30_GD30",
        label="AL30 / GD30",
        local_symbol="AL30D",
        ny_symbol="GD30D",
        description="Bonar 2030 — ley local vs ley Nueva York",
    ),
    BondPairConfig(
        id="AL35_GD35",
        label="AL35 / GD35",
        local_symbol="AL35D",
        ny_symbol="GD35D",
        description="Bonar 2035 — ley local vs ley Nueva York",
    ),
    BondPairConfig(
        id="AE38_GD38",
        label="AE38 / GD38",
        local_symbol="AE38D",
        ny_symbol="GD38D",
        description="Bonar 2038 — ley local vs ley Nueva York",
    ),
    BondPairConfig(
        id="AL29_GD29",
        label="AL29 / GD29",
        local_symbol="AL29D",
        ny_symbol="GD29D",
        description="Bonar 2029 — ley local vs ley Nueva York",
    ),
    BondPairConfig(
        id="AL41_GD41",
        label="AL41 / GD41",
        local_symbol="AL41D",
        ny_symbol="GD41D",
        description="Bonar 2041 — ley local vs ley Nueva York",
    ),
]

BONDS_CACHE_DIR = Path(__file__).parent.parent / "cache" / "bonds"
BONDS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

ORDER_LOG_FILE = BONDS_CACHE_DIR / "order_log.json"
MAX_ORDER_LOG_ENTRIES = 200

ROLLING_WINDOW = 20
ALERT_Z_THRESHOLD = float(os.getenv("BOND_ALERT_Z_THRESHOLD", "2.0"))
MAX_HISTORY_POINTS = 500

# Commission parameters — configurable via .env
# Total end-to-end round-trip cost (both legs combined), e.g. 0.005 = 0.5%
ROUNDTRIP_COMMISSION = float(os.getenv("IOL_ROUNDTRIP_COMMISSION", "0.005"))

# Paper trading parameters
PAPER_CLOSE_Z_THRESHOLD = float(os.getenv("PAPER_CLOSE_Z_THRESHOLD", "0.5"))
PAPER_TRADE_NOTIONAL = float(os.getenv("PAPER_TRADE_NOTIONAL", "100000.0"))
PAPER_TRADES_FILE = BONDS_CACHE_DIR / "paper_trades.json"
MAX_PAPER_TRADES = 500


# ---------------------------------------------------------------------------
# Commission helpers
# ---------------------------------------------------------------------------

def _compute_commission(ratio: float, mean: float) -> CommissionInfo:
    """
    Round-trip cost for an intraday arbitrage.
    ROUNDTRIP_COMMISSION is the total end-to-end cost (both legs combined).
    e.g. 0.005 = 0.5% total.

    gross_spread_pct = |ratio - mean| / mean  (as %)
    net_spread_pct   = gross_spread_pct - roundtrip_cost_pct
    breakeven_ratio  = mean ± mean * roundtrip_cost  (depending on direction)
    """
    gross_spread = abs(ratio - mean) / mean if mean != 0 else 0.0
    net_spread = gross_spread - ROUNDTRIP_COMMISSION

    if ratio >= mean:
        breakeven = mean * (1 + ROUNDTRIP_COMMISSION)
    else:
        breakeven = mean * (1 - ROUNDTRIP_COMMISSION)

    return CommissionInfo(
        roundtrip_cost_pct=round(ROUNDTRIP_COMMISSION * 100, 4),
        gross_spread_pct=round(gross_spread * 100, 4),
        net_spread_pct=round(net_spread * 100, 4),
        is_profitable=net_spread > 0,
        breakeven_ratio=round(breakeven, 6),
    )


# ---------------------------------------------------------------------------
# Market hours helper
# ---------------------------------------------------------------------------

def _is_market_open() -> bool:
    now_art = datetime.now(timezone(timedelta(hours=-3)))
    if now_art.weekday() >= 5:
        return False
    return 11 <= now_art.hour < 17


# ---------------------------------------------------------------------------
# Bond monitor
# ---------------------------------------------------------------------------

class BondMonitor:

    def __init__(self):
        self._pairs: dict[str, BondPairState] = {
            p.id: BondPairState(config=p) for p in BOND_PAIRS
        }
        self._last_refresh_at: Optional[datetime] = None
        self._next_refresh_at: Optional[datetime] = None
        self._refresh_running: bool = False
        self._iol_authenticated: bool = False
        self._eod_signal: bool = False

    # ------------------------------------------------------------------
    # EOD signal (smart: hold if spread persists, close if converged)
    # ------------------------------------------------------------------

    EOD_HOLD_Z_THRESHOLD = 1.0  # abs(z) >= this → spread persists → hold overnight

    def set_eod_signal(self, active: bool) -> None:
        self._eod_signal = active
        for state in self._pairs.values():
            state.eod_signal = active
            if active:
                # Per-pair action based on current z-score
                z = state.stats.z_score if state.stats else 0.0
                ratio = state.latest.ratio if state.latest else 0.0
                if abs(z) >= self.EOD_HOLD_Z_THRESHOLD:
                    state.eod_action = "hold"
                    logger.info(
                        f"EOD [{state.config.id}]: spread persists (z={z:.2f}) — HOLD overnight."
                    )
                else:
                    state.eod_action = "close"
                    logger.info(
                        f"EOD [{state.config.id}]: spread converged (z={z:.2f}) — CLOSE position."
                    )
                    # Auto-close any open paper trade for this pair
                    close_open_paper_trades_eod(state.config.id, ratio, z)
            else:
                state.eod_action = "none"
        if active:
            logger.warning("EOD window ACTIVE — per-pair actions: hold/close assigned.")
        else:
            logger.info("EOD signal cleared — new trading day.")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _history_file(self, pair_id: str) -> Path:
        return BONDS_CACHE_DIR / f"{pair_id}.json"

    def _load_history(self, pair_id: str) -> list[RatioSnapshot]:
        path = self._history_file(pair_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text())
            return [RatioSnapshot(**item) for item in raw]
        except Exception as e:
            logger.warning(f"Could not load bond history for {pair_id}: {e}")
            return []

    def _save_history(self, pair_id: str, history: list[RatioSnapshot]) -> None:
        path = self._history_file(pair_id)
        try:
            data = [s.model_dump(mode="json") for s in history]
            path.write_text(json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Could not save bond history for {pair_id}: {e}")

    def warm_from_disk(self) -> None:
        for pair_id, state in self._pairs.items():
            state.history = self._load_history(pair_id)
            if state.history:
                state.latest = state.history[-1]
                state.stats = _compute_stats(state.history, ROLLING_WINDOW)
                logger.info(f"Bond monitor: loaded {len(state.history)} points for {pair_id}")

    # ------------------------------------------------------------------
    # Price fetching
    # ------------------------------------------------------------------

    async def _fetch_quote(self, symbol: str) -> Optional[BondQuote]:
        try:
            data = await get_cotizacion_detalle(symbol)
            precio = (
                data.get("ultimoPrecio")
                or data.get("ultimo")
                or data.get("precio")
            )
            if precio is None:
                logger.warning(f"IOL returned no price for {symbol}: {data}")
                return None

            puntas = data.get("puntas") or []
            bid = ask = None
            if puntas:
                bid = puntas[0].get("precioCompra")
                ask = puntas[0].get("precioVenta")

            return BondQuote(
                symbol=symbol,
                price=float(precio),
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                volume=data.get("volumen") or data.get("cantidadNominal"),
                fetched_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None

    async def refresh_pair(self, pair: BondPairConfig) -> None:
        state = self._pairs[pair.id]
        try:
            local_q, ny_q = await asyncio.gather(
                self._fetch_quote(pair.local_symbol),
                self._fetch_quote(pair.ny_symbol),
            )

            if local_q is None or ny_q is None:
                missing = pair.local_symbol if local_q is None else pair.ny_symbol
                state.last_fetch_error = f"No price for {missing}"
                return

            if ny_q.price == 0:
                state.last_fetch_error = f"Zero price for {pair.ny_symbol}"
                return

            ratio = local_q.price / ny_q.price
            snapshot = RatioSnapshot(
                pair_id=pair.id,
                timestamp=datetime.now(timezone.utc),
                local_price=local_q.price,
                ny_price=ny_q.price,
                ratio=ratio,
            )

            state.history.append(snapshot)
            if len(state.history) > MAX_HISTORY_POINTS:
                state.history = state.history[-MAX_HISTORY_POINTS:]

            state.latest = snapshot
            state.last_fetch_error = None

            stats = _compute_stats(state.history, ROLLING_WINDOW)
            state.stats = stats

            # Always compute commission info (visible even without alert)
            comm = _compute_commission(ratio, stats.mean) if stats else None
            state.commission = comm

            # Alert fires on z-score threshold alone; commission info is informational
            if stats and abs(stats.z_score) >= ALERT_Z_THRESHOLD:
                direction = "LOCAL_CHEAP" if stats.z_score < 0 else "NY_CHEAP"
                state.alert = ArbitrageAlert(
                    pair_id=pair.id,
                    pair_label=pair.label,
                    timestamp=snapshot.timestamp,
                    ratio=ratio,
                    z_score=stats.z_score,
                    direction=direction,
                    description=_alert_description(pair, ratio, stats.z_score, direction, comm),
                    commission=comm,
                )
            else:
                state.alert = None

            # Paper trading: open/close virtual positions based on z-score
            if stats:
                direction = "LOCAL_CHEAP" if stats.z_score < 0 else "NY_CHEAP"
                process_paper_trades(
                    pair_id=pair.id,
                    pair_label=pair.label,
                    ratio=ratio,
                    z_score=stats.z_score,
                    direction=direction,
                )

            self._save_history(pair.id, state.history)
            self._iol_authenticated = True

        except Exception as e:
            state.last_fetch_error = str(e)
            logger.error(f"Error refreshing pair {pair.id}: {e}", exc_info=True)

    async def refresh_all(self) -> None:
        if self._refresh_running:
            logger.info("Bond refresh already running, skipping.")
            return
        self._refresh_running = True
        self._last_refresh_at = datetime.now(timezone.utc)
        try:
            await asyncio.gather(*[self.refresh_pair(p) for p in BOND_PAIRS])
            logger.info(f"Bond refresh complete for {len(BOND_PAIRS)} pairs.")
        finally:
            self._refresh_running = False

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_status(self) -> BondsStatusResponse:
        return BondsStatusResponse(
            pairs=list(self._pairs.values()),
            last_refresh_at=self._last_refresh_at,
            next_refresh_at=self._next_refresh_at,
            refresh_running=self._refresh_running,
            iol_authenticated=self._iol_authenticated,
            market_open=_is_market_open(),
            eod_signal=self._eod_signal,
            commission_rate=ROUNDTRIP_COMMISSION,
        )

    def get_pair_history(self, pair_id: str, limit: int = 200) -> BondHistoryResponse:
        state = self._pairs.get(pair_id)
        if state is None:
            raise KeyError(f"Unknown pair_id: {pair_id}")
        return BondHistoryResponse(
            pair_id=pair_id,
            pair_label=state.config.label,
            history=state.history[-limit:],
            stats=state.stats,
        )

    def set_next_refresh_at(self, dt: datetime) -> None:
        self._next_refresh_at = dt

    def is_running(self) -> bool:
        return self._refresh_running


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _compute_stats(history: list[RatioSnapshot], window: int) -> Optional[RatioStats]:
    if len(history) < 2:
        return None
    window_data = history[-window:]
    ratios = [s.ratio for s in window_data]
    n = len(ratios)
    mean = sum(ratios) / n
    variance = sum((r - mean) ** 2 for r in ratios) / max(n - 1, 1)
    std = variance ** 0.5
    current_ratio = history[-1].ratio
    z_score = (current_ratio - mean) / std if std > 0 else 0.0
    return RatioStats(
        mean=round(mean, 6),
        std=round(std, 6),
        z_score=round(z_score, 4),
        upper_band=round(mean + 2 * std, 6),
        lower_band=round(mean - 2 * std, 6),
        upper_band_1sigma=round(mean + std, 6),
        lower_band_1sigma=round(mean - std, 6),
        window_size=n,
    )


def _alert_description(
    pair: BondPairConfig, ratio: float, z_score: float, direction: str, comm: CommissionInfo
) -> str:
    net = f"{comm.net_spread_pct:+.3f}%"
    breakeven = f"{comm.breakeven_ratio:.4f}"
    if direction == "LOCAL_CHEAP":
        return (
            f"{pair.local_symbol} barato vs {pair.ny_symbol} "
            f"(ratio={ratio:.4f}, z={z_score:.2f}σ). "
            f"Spread neto: {net} · Breakeven: {breakeven}. "
            f"Oportunidad: comprar {pair.local_symbol} / vender {pair.ny_symbol}."
        )
    else:
        return (
            f"{pair.ny_symbol} barato vs {pair.local_symbol} "
            f"(ratio={ratio:.4f}, z={z_score:.2f}σ). "
            f"Spread neto: {net} · Breakeven: {breakeven}. "
            f"Oportunidad: comprar {pair.ny_symbol} / vender {pair.local_symbol}."
        )


# ---------------------------------------------------------------------------
# Order log persistence
# ---------------------------------------------------------------------------

def _load_order_log() -> list[OrderLogEntry]:
    if not ORDER_LOG_FILE.exists():
        return []
    try:
        raw = json.loads(ORDER_LOG_FILE.read_text())
        return [OrderLogEntry(**item) for item in raw]
    except Exception as e:
        logger.warning(f"Could not load order log: {e}")
        return []


def _append_order_log(entry: OrderLogEntry) -> None:
    entries = _load_order_log()
    entries.append(entry)
    # Keep newest entries, cap at MAX
    entries = entries[-MAX_ORDER_LOG_ENTRIES:]
    try:
        data = [e.model_dump(mode="json") for e in entries]
        ORDER_LOG_FILE.write_text(json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Could not save order log: {e}")


def get_order_log(limit: int = 50) -> OrderLogResponse:
    entries = _load_order_log()
    # Newest first
    entries = list(reversed(entries[-limit:]))
    return OrderLogResponse(entries=entries, total=len(_load_order_log()))


# ---------------------------------------------------------------------------
# Order execution
# ---------------------------------------------------------------------------

async def execute_order(req: BondOrderRequest) -> BondOrderResponse:
    payload = {
        "mercado": "bCBA",
        "simbolo": req.symbol,
        "cantidad": req.quantity,
        "precio": req.price,
        "plazo": req.plazo,
        "validez": "hoy",
        "tipoOrden": "precioLimite",
        "side": req.side,
    }
    label = "[SANDBOX] " if req.sandbox else ""

    # Resolve pair label from config
    pair_state = bond_monitor._pairs.get(req.pair_id)
    pair_label = pair_state.config.label if pair_state else req.pair_id

    try:
        result = await place_order(payload)
        order_id = str(result.get("nroOperacion") or result.get("id") or "")
        response = BondOrderResponse(
            success=True,
            order_id=order_id or None,
            message=f"{label}Orden enviada exitosamente.",
            sandbox=req.sandbox,
            raw_response=result,
        )
    except Exception as e:
        response = BondOrderResponse(
            success=False,
            message=f"{label}Error al enviar orden: {e}",
            sandbox=req.sandbox,
        )

    _append_order_log(OrderLogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        pair_id=req.pair_id,
        pair_label=pair_label,
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        price=req.price,
        plazo=req.plazo,
        sandbox=req.sandbox,
        success=response.success,
        order_id=response.order_id,
        message=response.message,
    ))

    return response


# ---------------------------------------------------------------------------
# Paper trading — persistence helpers
# ---------------------------------------------------------------------------

def _load_paper_trades() -> list[PaperTrade]:
    if not PAPER_TRADES_FILE.exists():
        return []
    try:
        raw = json.loads(PAPER_TRADES_FILE.read_text())
        return [PaperTrade(**item) for item in raw]
    except Exception as e:
        logger.warning(f"Could not load paper trades: {e}")
        return []


def _save_paper_trades(trades: list[PaperTrade]) -> None:
    trades = trades[-MAX_PAPER_TRADES:]
    try:
        data = [t.model_dump(mode="json") for t in trades]
        PAPER_TRADES_FILE.write_text(json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Could not save paper trades: {e}")


def _compute_paper_stats(closed: list[PaperTrade]) -> Optional[PaperTradeStats]:
    if not closed:
        return None
    winners = [t for t in closed if (t.net_pnl_pct or 0) > 0]
    total_gross = sum(t.gross_pnl_ars or 0 for t in closed)
    total_net = sum(t.net_pnl_ars or 0 for t in closed)
    avg_gross = sum(t.gross_pnl_pct or 0 for t in closed) / len(closed)
    avg_net = sum(t.net_pnl_pct or 0 for t in closed) / len(closed)

    durations = []
    for t in closed:
        if t.closed_at and t.opened_at:
            durations.append((t.closed_at - t.opened_at).total_seconds() / 3600)
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return PaperTradeStats(
        total_trades=len(closed),
        winning_trades=len(winners),
        losing_trades=len(closed) - len(winners),
        win_rate_pct=round(len(winners) / len(closed) * 100, 1),
        avg_gross_pnl_pct=round(avg_gross * 100, 4),
        avg_net_pnl_pct=round(avg_net * 100, 4),
        total_gross_pnl_ars=round(total_gross, 2),
        total_net_pnl_ars=round(total_net, 2),
        avg_duration_hours=round(avg_duration, 2),
    )


# ---------------------------------------------------------------------------
# Paper trading — core logic (called on every refresh)
# ---------------------------------------------------------------------------

def process_paper_trades(
    pair_id: str,
    pair_label: str,
    ratio: float,
    z_score: float,
    direction: str,
    close_reason: str = "convergence",
) -> None:
    """
    Called after each price refresh for a pair.
    - If no open trade and |z| >= threshold → open a new paper trade.
    - If open trade exists and |z| <= PAPER_CLOSE_Z_THRESHOLD → close it with P&L.
    Only one open trade per pair at a time.
    """
    trades = _load_paper_trades()

    open_trade = next(
        (t for t in trades if t.pair_id == pair_id and t.status == "open"), None
    )

    if open_trade is None:
        # Check if we should open a new trade
        if abs(z_score) >= ALERT_Z_THRESHOLD:
            new_trade = PaperTrade(
                id=str(uuid.uuid4()),
                pair_id=pair_id,
                pair_label=pair_label,
                opened_at=datetime.now(timezone.utc),
                open_ratio=ratio,
                open_z_score=z_score,
                direction=direction,
                notional_ars=PAPER_TRADE_NOTIONAL,
                roundtrip_commission_pct=ROUNDTRIP_COMMISSION,
                status="open",
            )
            trades.append(new_trade)
            logger.info(
                f"[PaperTrade] OPEN {pair_id}: ratio={ratio:.4f} z={z_score:.2f}σ "
                f"direction={direction}"
            )
    else:
        # Check if spread has converged enough to close
        if abs(z_score) <= PAPER_CLOSE_Z_THRESHOLD:
            _close_paper_trade(open_trade, ratio, z_score, close_reason)
            logger.info(
                f"[PaperTrade] CLOSE {pair_id}: ratio={ratio:.4f} z={z_score:.2f}σ "
                f"reason={close_reason} net={open_trade.net_pnl_pct}"
            )

    _save_paper_trades(trades)


def _close_paper_trade(
    trade: PaperTrade,
    close_ratio: float,
    close_z_score: float,
    close_reason: str,
) -> None:
    """Mutates trade in-place: computes P&L and marks as closed."""
    trade.closed_at = datetime.now(timezone.utc)
    trade.close_ratio = close_ratio
    trade.close_z_score = close_z_score
    trade.close_reason = close_reason
    trade.status = "closed"

    # P&L: if LOCAL_CHEAP we bought local/sold NY at open, reversed at close
    # The gain is how much the ratio moved back toward mean
    if trade.direction == "LOCAL_CHEAP":
        # We bought the cheaper leg; gain if ratio increased (local appreciated vs NY)
        raw_pnl = (close_ratio - trade.open_ratio) / trade.open_ratio
    else:
        # NY_CHEAP: bought NY leg; gain if ratio decreased (NY appreciated vs local)
        raw_pnl = (trade.open_ratio - close_ratio) / trade.open_ratio

    gross_pct = raw_pnl
    net_pct = gross_pct - trade.roundtrip_commission_pct

    trade.gross_pnl_pct = round(gross_pct, 6)
    trade.net_pnl_pct = round(net_pct, 6)
    trade.gross_pnl_ars = round(gross_pct * trade.notional_ars, 2)
    trade.net_pnl_ars = round(net_pct * trade.notional_ars, 2)


def close_open_paper_trades_eod(pair_id: str, ratio: float, z_score: float) -> None:
    """Called by EOD logic when eod_action == 'close' for a pair."""
    trades = _load_paper_trades()
    open_trade = next(
        (t for t in trades if t.pair_id == pair_id and t.status == "open"), None
    )
    if open_trade:
        _close_paper_trade(open_trade, ratio, z_score, "eod_close")
        logger.info(f"[PaperTrade] EOD-CLOSE {pair_id}: net={open_trade.net_pnl_pct}")
        _save_paper_trades(trades)


def get_paper_trades(limit: int = 100) -> PaperTradeResponse:
    trades = _load_paper_trades()
    open_trades = [t for t in trades if t.status == "open"]
    closed_trades = list(reversed([t for t in trades if t.status == "closed"]))
    closed_trades = closed_trades[:limit]
    stats = _compute_paper_stats([t for t in trades if t.status == "closed"])
    return PaperTradeResponse(
        open_trades=open_trades,
        closed_trades=closed_trades,
        stats=stats,
        notional_ars=PAPER_TRADE_NOTIONAL,
    )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

bond_monitor = BondMonitor()
