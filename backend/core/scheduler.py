import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import REFRESH_HOUR_UTC, REFRESH_MINUTE_UTC, DJIA_TICKERS, NDX_TICKERS

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_refresh_running = False


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

        # Fix index membership
        for s in stocks:
            membership = []
            if s.ticker in djia_set:
                membership.append("DJIA")
            if s.ticker in ndx_set:
                membership.append("NDX")
            membership.append("SP500")  # all tickers treated as SP500 universe
            s.index_membership = list(set(membership))

        stock_cache.set_batch(stocks)
        logger.info(f"Daily refresh complete. {len(stocks)} tickers cached.")
    except Exception as e:
        logger.error(f"Daily refresh failed: {e}", exc_info=True)
    finally:
        _refresh_running = False


def is_refresh_running() -> bool:
    return _refresh_running


def start_scheduler():
    """Configure and start the APScheduler."""
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
    scheduler.start()
    logger.info("Scheduler started. Daily refresh at 22:30 UTC on weekdays.")
