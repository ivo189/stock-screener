"""
Screener de call ratio spreads (compro X calls en A, vendo Y > X calls en B > A, a crédito).

1) scan_underlyings: acciones cerca de un máximo (ATH / 52w / 26w / 13w) con vol realizada alta.
2) find_ratio_spreads: para un subyacente, recorre vencimientos y arma combinaciones
   de strikes con yfinance (IV, OI y bid/ask reales de la cadena).
"""
import logging
import time
from datetime import date, datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from services import options_math as om
from services.universe import get_full_universe

logger = logging.getLogger(__name__)

HIGH_WINDOWS = {"ath": None, "52w": 252, "26w": 126, "13w": 63}
SCAN_TTL_SECONDS = 30 * 60
_scan_cache: dict[tuple, tuple[float, list[dict]]] = {}


def _chunks(items: list[str], n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _download(tickers: list[str], period: str) -> pd.DataFrame:
    return yf.download(
        tickers, period=period, interval="1d", auto_adjust=False,
        group_by="ticker", threads=True, progress=False,
    )


def _frame(df: pd.DataFrame, ticker: str, single: bool) -> Optional[pd.DataFrame]:
    try:
        sub = df if single else df[ticker]
        sub = sub[["Close", "High", "Volume"]].dropna(subset=["Close"])
        return sub if len(sub) else None
    except Exception:
        return None


def scan_underlyings(
    universe: list[str],
    high_ref: str = "ath",
    max_dist_pct: float = 8.0,
    min_vol_pct: float = 30.0,
    min_traded_musd: float = 300.0,
    top: int = 30,
    force: bool = False,
) -> list[dict]:
    """Devuelve subyacentes rankeados por score = RV21 - 3*|dist al máximo|."""
    if high_ref not in HIGH_WINDOWS:
        raise ValueError(f"high_ref debe ser uno de {list(HIGH_WINDOWS)}")
    key = (tuple(sorted(universe)), high_ref, max_dist_pct, min_vol_pct, min_traded_musd, top)
    hit = _scan_cache.get(key)
    if hit and not force and time.time() - hit[0] < SCAN_TTL_SECONDS:
        return hit[1]

    tickers = get_full_universe(universe) if all(u in ("SP500", "DJIA", "NDX") for u in universe) else universe

    # Paso 1: 1 año de datos, prefiltro barato (cerca del máx 52w o más)
    pre: dict[str, float] = {}
    for chunk in _chunks(tickers, 100):
        try:
            df = _download(chunk, "1y")
        except Exception as e:
            logger.warning(f"yf.download falló en chunk: {e}")
            continue
        for t in chunk:
            f = _frame(df, t, single=len(chunk) == 1)
            if f is None or len(f) < 60:
                continue
            close, hi52 = float(f["Close"].iloc[-1]), float(f["High"].max())
            # Si el máximo de referencia es más largo que 52w, el máx real es >= hi52,
            # así que alcanza con que esté a menos de max_dist+15% del máx 52w.
            if close >= hi52 * (1 - (max_dist_pct + 15) / 100):
                pre[t] = close

    # Paso 2: historia completa (ATH real, sin ajustar por dividendos) para los sobrevivientes
    rows: list[dict] = []
    survivors = list(pre)
    period = "max" if high_ref == "ath" else "2y"
    for chunk in _chunks(survivors, 50):
        try:
            df = _download(chunk, period)
        except Exception as e:
            logger.warning(f"yf.download (full) falló: {e}")
            continue
        for t in chunk:
            f = _frame(df, t, single=len(chunk) == 1)
            if f is None or len(f) < 30:
                continue
            closes = f["Close"].tolist()
            window = HIGH_WINDOWS[high_ref]
            high = float(f["High"].max() if window is None else f["High"].iloc[-window:].max())
            close = closes[-1]
            dist = om.dist_to_high_pct(close, high)
            vol = om.realized_vol(closes, 21)
            if dist is None or vol is None or dist < -max_dist_pct or vol < min_vol_pct:
                continue
            traded = float(f["Close"].iloc[-30:].mean() * f["Volume"].iloc[-30:].mean()) / 1e6
            if traded < min_traded_musd:
                continue
            rows.append({
                "ticker": t,
                "close": round(close, 2),
                "high_ref": round(high, 2),
                "dist_pct": round(dist, 2),
                "rv21": round(vol, 1),
                "max_move_pct": round(om.biggest_daily_move(closes, 21) or 0.0, 2),
                "sigma15_pct": round(om.sigma_move_pct(vol, 15), 2),
                "traded_musd": round(traded),
                "score": round(om.underlying_score(vol, dist), 1),
                "last_date": f.index[-1].strftime("%Y-%m-%d"),
            })

    rows.sort(key=lambda r: r["score"], reverse=True)
    rows = rows[:top]
    for r in rows:
        r.update(_earnings_info(r["ticker"]))
    _scan_cache[key] = (time.time(), rows)
    return rows


def _earnings_info(ticker: str) -> dict:
    try:
        cal = yf.Ticker(ticker).calendar
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates:
            d = dates[0]
            d = d if isinstance(d, date) else pd.Timestamp(d).date()
            return {"earnings_date": d.isoformat(), "days_to_earnings": (d - date.today()).days}
    except Exception:
        pass
    return {"earnings_date": None, "days_to_earnings": None}


def find_ratio_spreads(
    ticker: str,
    x: int = 1,
    y: int = 3,
    min_dte: int = 14,
    max_dte: int = 45,
    min_credit: float = 0.0,
    max_otm_long_pct: float = 5.0,
    max_otm_short_pct: float = 25.0,
    min_open_interest: int = 50,
    max_rel_spread: float = 0.35,
    top: int = 25,
) -> dict:
    om.validate_ratio(x, y)
    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d", auto_adjust=False)
    if hist.empty:
        raise ValueError(f"Sin precio para {ticker}")
    spot = float(hist["Close"].iloc[-1])

    today = date.today()
    results: list[dict] = []
    for exp in tk.options:
        dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
        if dte < min_dte or dte > max_dte:
            continue
        try:
            chain = tk.option_chain(exp).calls
        except Exception as e:
            logger.warning(f"{ticker} {exp}: option_chain falló: {e}")
            continue
        calls = [
            {"strike": float(r.strike), "bid": _f(r.bid), "ask": _f(r.ask), "last": _f(r.lastPrice),
             "oi": int(r.openInterest) if pd.notna(r.openInterest) else 0,
             "iv": _f(r.impliedVolatility)}
            for r in chain.itertuples()
        ]
        iv_by_strike = {c["strike"]: c["iv"] for c in calls}
        for sp in om.build_spreads(
            calls, spot, x, y, min_credit, max_otm_long_pct, max_otm_short_pct,
            min_open_interest, max_rel_spread,
        ):
            ub = sp.upper_breakeven
            results.append({
                "expiration": exp,
                "dte": dte,
                "k_long": sp.k_long,
                "k_short": sp.k_short,
                "premium_long": round(sp.premium_long, 2),
                "premium_short": round(sp.premium_short, 2),
                "net_credit": round(sp.net_credit * sp.multiplier, 2),
                "max_profit": round(sp.max_profit * sp.multiplier, 2),
                "upper_breakeven": round(ub, 2) if ub else None,
                "upper_breakeven_pct": round((ub / spot - 1) * 100, 2) if ub else None,
                "naked": sp.naked,
                "iv_long": iv_by_strike.get(sp.k_long),
                "iv_short": iv_by_strike.get(sp.k_short),
                "payoff": sp.payoff_curve(spot * 0.85, spot * 1.35),
            })

    # Ranking: máximo colchón hasta el breakeven superior, desempate por ganancia máxima.
    results.sort(key=lambda r: (-(r["upper_breakeven_pct"] or 0), -r["max_profit"]))
    return {"ticker": ticker, "spot": round(spot, 2), "x": x, "y": y, "spreads": results[:top]}


def _f(v) -> Optional[float]:
    try:
        return None if v is None or pd.isna(v) else float(v)
    except Exception:
        return None
