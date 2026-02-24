import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import REFRESH_HOUR_UTC, REFRESH_MINUTE_UTC, DJIA_TICKERS, NDX_TICKERS

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_refresh_running = False

# ---------------------------------------------------------------------------
# Market hours guard (BCBA: 11:00 – 17:00 ART = UTC-3)
# ---------------------------------------------------------------------------
MARKET_OPEN_HOUR_ART = 11
MARKET_CLOSE_HOUR_ART = 17

# Minutes before market close to trigger end-of-day cash-out signal
EOD_SIGNAL_MINUTES_BEFORE_CLOSE = 10


def _is_market_open() -> bool:
    """Return True if we are within BCBA trading hours (Mon-Fri 11:00-17:00 ART)."""
    now_art = datetime.now(timezone(timedelta(hours=-3)))
    if now_art.weekday() >= 5:          # Saturday / Sunday
        return False
    return MARKET_OPEN_HOUR_ART <= now_art.hour < MARKET_CLOSE_HOUR_ART


async def run_full_refresh():
    """Fetch all universe tickers and update cache."""
    global _refresh_running
    if _refresh_running:
        logger.info("Refresh already running, skipping.")
        return
    _refresh_running = True
    try:
        from core.cache import stock_cache
        from services.universe import get_full_universe
        from services.data_fetcher import batch_fetch_universe

        logger.info("Starting daily data refresh...")
        tickers = get_full_universe(["SP500", "DJIA", "NDX"])
        djia_set = set(DJIA_TICKERS)
        ndx_set = set(NDX_TICKERS)

        def progress(done, total):
            if done % 50 == 0 or done == total:
                logger.info(f"Refresh progress: {done}/{total}")

        stocks = batch_fetch_universe(tickers, djia_set, progress_callback=progress)

        for s in stocks:
            membership = []
            if s.ticker in djia_set:
                membership.append("DJIA")
            if s.ticker in ndx_set:
                membership.append("NDX")
            membership.append("SP500")
            s.index_membership = list(set(membership))

        stock_cache.set_batch(stocks)
        logger.info(f"Daily refresh complete. {len(stocks)} tickers cached.")
    except Exception as e:
        logger.error(f"Daily refresh failed: {e}", exc_info=True)
    finally:
        _refresh_running = False


def is_refresh_running() -> bool:
    return _refresh_running


async def run_bond_refresh():
    """
    Intraday bond price refresh — runs every 15 min but only during market hours.
    Also fires an end-of-day cash signal 10 min before market close.
    """
    from services.bond_service import bond_monitor

    now_art = datetime.now(timezone(timedelta(hours=-3)))
    hour = now_art.hour
    minute = now_art.minute

    # Check if we're in the EOD window (e.g. 16:50 ART = close - 10 min)
    eod_start = MARKET_CLOSE_HOUR_ART * 60 - EOD_SIGNAL_MINUTES_BEFORE_CLOSE
    current_minutes = hour * 60 + minute
    is_eod = (
        now_art.weekday() < 5
        and eod_start <= current_minutes < MARKET_CLOSE_HOUR_ART * 60
    )

    if not _is_market_open() and not is_eod:
        logger.debug("Bond refresh skipped — outside market hours.")
        return

    if is_eod:
        logger.info("EOD signal: market closing soon — emitting end-of-day cash signal.")
        bond_monitor.set_eod_signal(active=True)

    logger.info("Scheduled bond refresh starting (intraday)...")
    await bond_monitor.refresh_all()


async def run_eod_reset():
    """Reset the EOD cash signal at market open the next day."""
    from services.bond_service import bond_monitor
    bond_monitor.set_eod_signal(active=False)
    logger.info("EOD signal reset — new trading day started.")


def start_scheduler():
    """Configure and start the APScheduler."""
    # Daily stock universe refresh (after market close)
    scheduler.add_job(
        run_full_refresh,
        trigger=CronTrigger(
            hour=REFRESH_HOUR_UTC,
            minute=REFRESH_MINUTE_UTC,
            day_of_week="mon-fri",
        ),
        id="daily_refresh",
        replace_existing=True,
        name="Daily market data refresh (17:30 ET / 22:30 UTC)",
    )

    # Intraday bond refresh every 15 minutes (guard inside the function)
    scheduler.add_job(
        run_bond_refresh,
        trigger=IntervalTrigger(minutes=15),
        id="bond_intraday_refresh",
        replace_existing=True,
        name="Intraday bond ratio refresh (15 min, market hours only)",
    )

    # Reset EOD signal at 11:00 ART (14:00 UTC) on trading days
    scheduler.add_job(
        run_eod_reset,
        trigger=CronTrigger(hour=14, minute=0, day_of_week="mon-fri"),
        id="bond_eod_reset",
        replace_existing=True,
        name="Reset EOD cash signal at market open",
    )

    scheduler.start()
    logger.info(
        "Scheduler started. "
        "Stock: 22:30 UTC weekdays. "
        "Bonds: every 15 min during market hours (11:00-17:00 ART)."
    )
