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

        # Forward dividend yield preferred over trailing.
        # yfinance returns these as decimals (e.g. 0.0142 = 1.42%) in most versions,
        # but some versions / tickers return them already as percentages (e.g. 1.42).
        # Guard: if raw value > 0.20 it's already a percentage — don't multiply.
        fwd_div = _safe_float(info.get("dividendYield"))
        trail_div = _safe_float(info.get("trailingAnnualDividendYield"))
        div_yield_raw = fwd_div if fwd_div is not None else trail_div
        if div_yield_raw is not None and div_yield_raw > 0:
            if div_yield_raw > 0.20:
                # Already expressed as a percentage (e.g. 1.42 meaning 1.42%)
                metrics.dividend_yield = round(div_yield_raw, 3)
            else:
                # Decimal form (e.g. 0.0142) — convert to percentage
                metrics.dividend_yield = round(div_yield_raw * 100, 3)
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

        # --- Weekly price history (5 years for Monte Carlo, last 52w for chart) ---
        try:
            hist_5y = t.history(period="5y", interval="1wk")
            if not hist_5y.empty and "Close" in hist_5y.columns:
                closes_5y = hist_5y["Close"].dropna()
                # Store full 5y history for Monte Carlo return estimation
                metrics.weekly_prices_5y = [
                    WeeklyPrice(date=str(idx.date()), close=round(float(v), 4))
                    for idx, v in closes_5y.items()
                ]
                # Use only last 52 weeks for the 1y chart
                closes = closes_5y.iloc[-52:] if len(closes_5y) >= 52 else closes_5y
            else:
                closes = pd.Series(dtype=float)

            if not closes.empty:
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

                # --- Moving averages ---
                # MA30w: 30-week SMA from weekly data
                if len(closes) >= 10:
                    ma30w_val = closes.iloc[-30:].mean() if len(closes) >= 30 else closes.mean()
                    metrics.ma_30w = round(float(ma30w_val), 4)
                    if metrics.current_price and metrics.ma_30w > 0:
                        metrics.pct_vs_ma30w = round(
                            (metrics.current_price - metrics.ma_30w) / metrics.ma_30w * 100, 2
                        )
        except Exception as e:
            logger.warning(f"{ticker}: price history failed: {e}")

        # --- Daily history for MA200d ---
        try:
            daily = t.history(period="1y", interval="1d")
            if not daily.empty and "Close" in daily.columns:
                daily_closes = daily["Close"].dropna()
                if len(daily_closes) >= 20:
                    ma200_val = daily_closes.iloc[-200:].mean() if len(daily_closes) >= 200 else daily_closes.mean()
                    metrics.ma_200d = round(float(ma200_val), 4)
                    if metrics.current_price and metrics.ma_200d > 0:
                        metrics.pct_vs_ma200d = round(
                            (metrics.current_price - metrics.ma_200d) / metrics.ma_200d * 100, 2
                        )
        except Exception as e:
            logger.warning(f"{ticker}: daily history for MA200 failed: {e}")

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
