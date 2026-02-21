import logging
import math
import time
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from config import YFINANCE_REQUEST_DELAY_SECONDS, DJIA_TICKERS
from models.stock import StockMetrics, WeeklyPrice

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return float(val)
    except Exception:
        return None


def calculate_eps_cagr(eps_values: list[float]) -> Optional[float]:
    """
    Calculate EPS CAGR from a list of annual EPS values (oldest to newest).
    Returns percentage (e.g. 8.5 for 8.5%).
    Returns None if data is insufficient or EPS is negative at either endpoint.
    """
    clean = [v for v in eps_values if v is not None and not math.isnan(v)]
    if len(clean) < 3:
        return None
    start, end = clean[0], clean[-1]
    n = len(clean) - 1
    if start <= 0 or end <= 0:
        return None
    try:
        cagr = (end / start) ** (1 / n) - 1
        return round(cagr * 100, 2)
    except Exception:
        return None


def calculate_price_volatility(weekly_closes: pd.Series) -> Optional[float]:
    """Annualized volatility from weekly log returns."""
    if len(weekly_closes) < 10:
        return None
    try:
        log_returns = np.log(weekly_closes / weekly_closes.shift(1)).dropna()
        if len(log_returns) < 5:
            return None
        vol_weekly = log_returns.std()
        vol_annual = vol_weekly * math.sqrt(52)
        return round(float(vol_annual), 4)
    except Exception:
        return None


def _extract_eps_history(ticker_obj: yf.Ticker) -> list[float]:
    """Extract up to 5 years of annual diluted EPS from financials."""
    try:
        fin = ticker_obj.financials  # columns = dates (newest first)
        if fin is None or fin.empty:
            return []
        # Look for Diluted EPS or Basic EPS row
        eps_row = None
        for label in ["Diluted EPS", "Basic EPS", "Earnings Per Share"]:
            if label in fin.index:
                eps_row = fin.loc[label]
                break
        if eps_row is None:
            return []
        # Sort ascending (oldest first), take last 5
        eps_sorted = eps_row.sort_index()
        values = [_safe_float(v) for v in eps_sorted.values[-5:]]
        return [v for v in values if v is not None]
    except Exception as e:
        logger.debug(f"EPS history extraction failed: {e}")
        return []


def fetch_stock_metrics(ticker: str, djia_set: set) -> StockMetrics:
    """
    Fetch all metrics for a single ticker using yfinance.
    Never raises — returns a partial StockMetrics on any error.
    """
    metrics = StockMetrics(ticker=ticker, last_updated=datetime.utcnow())
    quality_fields = 0
    total_fields = 8  # fields we track for quality score

    try:
        t = yf.Ticker(ticker)

        # --- Fundamentals from .info ---
        info = {}
        try:
            info = t.info or {}
        except Exception as e:
            logger.warning(f"{ticker}: .info failed: {e}")

        metrics.name = info.get("longName") or info.get("shortName") or ticker
        metrics.sector = info.get("sector")
        metrics.industry = info.get("industry")

        metrics.current_price = _safe_float(
            info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        )
        if metrics.current_price:
            quality_fields += 1

        metrics.price_52w_high = _safe_float(info.get("fiftyTwoWeekHigh"))
        metrics.price_52w_low = _safe_float(info.get("fiftyTwoWeekLow"))

        if metrics.current_price and metrics.price_52w_low and metrics.price_52w_low > 0:
            metrics.pct_above_52w_low = round(
                (metrics.current_price - metrics.price_52w_low) / metrics.price_52w_low * 100, 2
            )
            quality_fields += 1

        metrics.trailing_pe = _safe_float(info.get("trailingPE"))
        if metrics.trailing_pe and metrics.trailing_pe > 0:
            quality_fields += 1

        metrics.forward_pe = _safe_float(info.get("forwardPE"))
        metrics.market_cap = _safe_float(info.get("marketCap"))

        div_yield = _safe_float(info.get("dividendYield"))
        if div_yield is not None:
            metrics.dividend_yield = round(div_yield * 100, 3)
            quality_fields += 1
        else:
            metrics.dividend_yield = 0.0

        metrics.eps_ttm = _safe_float(info.get("trailingEps"))
        metrics.beta = _safe_float(info.get("beta"))
        if metrics.beta is not None:
            quality_fields += 1

        # --- EPS CAGR from financials ---
        eps_history = _extract_eps_history(t)
        if eps_history:
            metrics.eps_cagr_5y = calculate_eps_cagr(eps_history)
            if metrics.eps_cagr_5y is not None:
                quality_fields += 1

        # --- Weekly price history (1 year) ---
        try:
            hist = t.history(period="1y", interval="1wk")
            if not hist.empty and "Close" in hist.columns:
                closes = hist["Close"].dropna()
                metrics.price_volatility_1y = calculate_price_volatility(closes)
                if metrics.price_volatility_1y:
                    quality_fields += 1

                metrics.weekly_prices = [
                    WeeklyPrice(date=str(idx.date()), close=round(float(v), 4))
                    for idx, v in closes.items()
                ]

                # Recompute 52w low/high from actual history if info values missing
                if not metrics.price_52w_low:
                    metrics.price_52w_low = round(float(closes.min()), 4)
                if not metrics.price_52w_high:
                    metrics.price_52w_high = round(float(closes.max()), 4)
                if metrics.current_price and metrics.price_52w_low and metrics.price_52w_low > 0:
                    metrics.pct_above_52w_low = round(
                        (metrics.current_price - metrics.price_52w_low) / metrics.price_52w_low * 100, 2
                    )
                    quality_fields = max(quality_fields, 2)  # ensure counted
        except Exception as e:
            logger.warning(f"{ticker}: price history failed: {e}")

        # --- Index membership ---
        membership = []
        if ticker in djia_set:
            membership.append("DJIA")
        membership.append("SP500")  # assume SP500 if in universe; filtered later
        metrics.index_membership = membership

        metrics.data_quality_score = round(quality_fields / total_fields, 2)

    except Exception as e:
        logger.error(f"{ticker}: unexpected fetch error: {e}")

    return metrics


def batch_fetch_universe(
    tickers: list[str],
    djia_set: set,
    progress_callback=None,
) -> list[StockMetrics]:
    """
    Fetch metrics for all tickers with rate limiting.
    Calls progress_callback(done, total) after each ticker.
    """
    results = []
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        try:
            m = fetch_stock_metrics(ticker, djia_set)
            results.append(m)
        except Exception as e:
            logger.error(f"batch_fetch: {ticker} failed: {e}")
        if progress_callback:
            progress_callback(i + 1, total)
        time.sleep(YFINANCE_REQUEST_DELAY_SECONDS)
    return results
