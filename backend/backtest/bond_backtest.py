"""
Bond Arbitrage Backtest — IOL historical daily data
====================================================
Fetches ~14 months of daily closing prices for all pairs from IOL,
then runs a grid search over:
  - open_z    : [1.0, 1.5, 2.0, 2.5]   (entry threshold)
  - close_z   : [0.0, 0.5, 1.0]        (exit threshold)
  - stop_z    : [None, 3.0, 4.0]        (stop-loss, None = no stop)
  - window    : [10, 20, 40]            (Bollinger rolling window)

For each parameter set computes per-trade P&L and summary stats.
Results printed as a ranked table and saved to backtest/results.csv.
"""
import asyncio
import os
import sys
from datetime import datetime, date
from pathlib import Path
from itertools import product

# -- path setup so we can import project modules --
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
import pandas as pd
import numpy as np
from typing import Optional

# ---------------------------------------------------------------------------
# Standalone token fetcher (avoids module-level asyncio.Lock conflict)
# ---------------------------------------------------------------------------

IOL_TOKEN_URL = "https://api.invertironline.com/token"
_cached_token: str = ""


async def get_bearer_token() -> str:
    """Fetch a fresh IOL bearer token directly (no shared state)."""
    global _cached_token
    if _cached_token:
        return _cached_token
    username = os.getenv("IOL_USERNAME", "")
    password = os.getenv("IOL_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("IOL_USERNAME and IOL_PASSWORD must be set in .env")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            IOL_TOKEN_URL,
            content=f"username={username}&password={password}&grant_type=password",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
    _cached_token = data["access_token"]
    return _cached_token

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PAIRS = [
    ("AL30D", "GD30D", "AL30/GD30"),
    ("AL35D", "GD35D", "AL35/GD35"),
    ("AE38D", "GD38D", "AE38/GD38"),
    ("AL29D", "GD29D", "AL29/GD29"),
    ("AL41D", "GD41D", "AL41/GD41"),
]

DATE_FROM = "2024-01-01"
DATE_TO   = date.today().strftime("%Y-%m-%d")

# Grid search parameters
OPEN_Z_VALUES  = [1.0, 1.5, 2.0, 2.5]
CLOSE_Z_VALUES = [0.0, 0.5, 1.0]
STOP_Z_VALUES  = [None, 3.0, 4.0]
WINDOW_VALUES  = [10, 20, 40]

OUTPUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

async def fetch_series(symbol: str, date_from: str, date_to: str) -> pd.Series:
    token = await get_bearer_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = (
        f"https://api.invertironline.com/api/v2/bCBA/Titulos/{symbol}"
        f"/Cotizacion/seriehistorica/{date_from}/{date_to}/sinAjustar"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

    records = [
        {"date": d["fechaHora"][:10], "price": d["ultimoPrecio"]}
        for d in data
        if d.get("ultimoPrecio") and d["ultimoPrecio"] > 0
    ]
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").set_index("date")["price"]
    return df


async def fetch_all_pairs() -> dict:
    print("Fetching historical data from IOL...")
    result = {}
    for local_sym, ny_sym, label in PAIRS:
        print(f"  {label}...", end=" ", flush=True)
        local_s, ny_s = await asyncio.gather(
            fetch_series(local_sym, DATE_FROM, DATE_TO),
            fetch_series(ny_sym, DATE_FROM, DATE_TO),
        )
        df = pd.DataFrame({"local": local_s, "ny": ny_s}).dropna()
        df["ratio"] = df["local"] / df["ny"]
        print(f"{len(df)} days")
        result[label] = df
    return result

# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(
    ratio: pd.Series,
    open_z: float,
    close_z: float,
    stop_z: Optional[float],
    window: int,
) -> list[dict]:
    """
    Simulate trades on a ratio series.
    Returns list of trade dicts with P&L info.
    """
    # Rolling Bollinger stats
    mean = ratio.rolling(window).mean()
    std  = ratio.rolling(window).std()
    z    = (ratio - mean) / std.replace(0, np.nan)

    trades = []
    position = None  # None or dict with entry info

    for i in range(window, len(ratio)):
        r   = ratio.iloc[i]
        zi  = z.iloc[i]
        dt  = ratio.index[i]

        if pd.isna(zi):
            continue

        if position is None:
            # Entry
            if abs(zi) >= open_z:
                direction = "LOCAL_CHEAP" if zi < 0 else "NY_CHEAP"
                position = {
                    "open_date": dt,
                    "open_ratio": r,
                    "open_z": zi,
                    "direction": direction,
                }
        else:
            # Check exit conditions
            exit_reason = None

            # Stop loss
            if stop_z is not None and abs(zi) >= stop_z:
                # Spread widened further — stop out
                # P&L is negative (spread moved against us)
                exit_reason = "stop_loss"

            # Take profit / convergence
            elif abs(zi) <= close_z:
                exit_reason = "convergence"

            if exit_reason:
                direction = position["direction"]
                open_r    = position["open_ratio"]

                # P&L: we profit when spread reverts
                if direction == "LOCAL_CHEAP":
                    # Bought cheap local, sold expensive NY → profit if ratio rises back
                    raw_pnl = (r - open_r) / open_r
                else:
                    # Bought cheap NY, sold expensive local → profit if ratio falls back
                    raw_pnl = (open_r - r) / open_r

                duration = (dt - position["open_date"]).days

                trades.append({
                    "open_date":    position["open_date"],
                    "close_date":   dt,
                    "direction":    direction,
                    "open_ratio":   open_r,
                    "close_ratio":  r,
                    "open_z":       position["open_z"],
                    "close_z":      zi,
                    "pnl_pct":      raw_pnl * 100,
                    "duration_days": duration,
                    "exit_reason":  exit_reason,
                })
                position = None

    # Mark open position at end of series as unrealised
    if position is not None:
        trades.append({
            "open_date":     position["open_date"],
            "close_date":    None,
            "direction":     position["direction"],
            "open_ratio":    position["open_ratio"],
            "close_ratio":   None,
            "open_z":        position["open_z"],
            "close_z":       None,
            "pnl_pct":       None,
            "duration_days": None,
            "exit_reason":   "open",
        })

    return trades


def summarise(trades: list[dict]) -> dict:
    closed = [t for t in trades if t["exit_reason"] != "open"]
    if not closed:
        return {"n_trades": 0}

    pnls = [t["pnl_pct"] for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    stops = [t for t in closed if t["exit_reason"] == "stop_loss"]
    durations = [t["duration_days"] for t in closed if t["duration_days"] is not None]

    return {
        "n_trades":          len(closed),
        "win_rate":          len(wins) / len(closed) * 100,
        "avg_pnl_pct":       np.mean(pnls),
        "total_pnl_pct":     np.sum(pnls),
        "avg_win_pct":       np.mean(wins) if wins else 0,
        "avg_loss_pct":      np.mean(losses) if losses else 0,
        "profit_factor":     abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else np.inf,
        "n_stops":           len(stops),
        "avg_duration_days": np.mean(durations) if durations else 0,
        "sharpe_approx":     np.mean(pnls) / np.std(pnls) if len(pnls) > 1 and np.std(pnls) > 0 else 0,
    }

# ---------------------------------------------------------------------------
# Grid search
# ---------------------------------------------------------------------------

def grid_search(pair_label: str, ratio: pd.Series) -> pd.DataFrame:
    rows = []
    combos = list(product(OPEN_Z_VALUES, CLOSE_Z_VALUES, STOP_Z_VALUES, WINDOW_VALUES))
    for open_z, close_z, stop_z, window in combos:
        if close_z >= open_z:
            continue  # nonsensical: exit at same or higher z than entry
        trades = run_backtest(ratio, open_z, close_z, stop_z, window)
        stats  = summarise(trades)
        rows.append({
            "pair":     pair_label,
            "open_z":   open_z,
            "close_z":  close_z,
            "stop_z":   stop_z if stop_z else "none",
            "window":   window,
            **stats,
        })
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_top(df: pd.DataFrame, n: int = 20):
    df_clean = df[df["n_trades"] > 0].copy()
    if df_clean.empty:
        print("No trades generated.")
        return

    df_clean = df_clean.sort_values("total_pnl_pct", ascending=False)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}" if isinstance(x, float) else str(x))

    cols = ["pair","open_z","close_z","stop_z","window",
            "n_trades","win_rate","avg_pnl_pct","total_pnl_pct",
            "profit_factor","n_stops","avg_duration_days","sharpe_approx"]
    print(df_clean[cols].head(n).to_string(index=False))


async def main():
    pair_data = await fetch_all_pairs()
    all_results = []

    for label, df in pair_data.items():
        print(f"\nRunning grid search for {label}...")
        result_df = grid_search(label, df["ratio"])
        all_results.append(result_df)

    combined = pd.concat(all_results, ignore_index=True)

    # Save full results
    out_file = OUTPUT_DIR / "results.csv"
    combined.to_csv(out_file, index=False)
    print(f"\nFull results saved to {out_file}")

    # --- Summary by parameter combo (across all pairs) ---
    print("\n" + "="*80)
    print("TOP 20 CONFIGS — ranked by total P&L % (summed across all pairs)")
    print("="*80)

    agg = (
        combined[combined["n_trades"] > 0]
        .groupby(["open_z","close_z","stop_z","window"])
        .agg(
            total_trades  = ("n_trades", "sum"),
            avg_win_rate  = ("win_rate", "mean"),
            total_pnl_pct = ("total_pnl_pct", "sum"),
            avg_pnl_pct   = ("avg_pnl_pct", "mean"),
            profit_factor = ("profit_factor", "mean"),
            avg_duration  = ("avg_duration_days", "mean"),
            total_stops   = ("n_stops", "sum"),
        )
        .reset_index()
        .sort_values("total_pnl_pct", ascending=False)
    )
    print(agg.head(20).to_string(index=False))

    # --- Best config per pair ---
    print("\n" + "="*80)
    print("BEST CONFIG PER PAIR (by total P&L %)")
    print("="*80)
    best = (
        combined[combined["n_trades"] > 0]
        .sort_values("total_pnl_pct", ascending=False)
        .groupby("pair")
        .first()
        .reset_index()
    )
    print(best[["pair","open_z","close_z","stop_z","window",
                "n_trades","win_rate","total_pnl_pct","avg_pnl_pct",
                "profit_factor","avg_duration_days"]].to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
