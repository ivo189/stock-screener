import math
import numpy as np
from typing import Optional


def run_monte_carlo(
    weekly_returns: list[float],
    initial_capital: float,
    n_simulations: int = 500,
    n_weeks: int = 52,
) -> dict:
    """
    Run Monte Carlo simulation on portfolio weekly returns.

    weekly_returns: list of historical weekly portfolio returns (as decimals, e.g. 0.012)
    initial_capital: starting portfolio value in USD
    n_simulations: number of simulation paths
    n_weeks: number of weeks to simulate (default 52 = 1 year)

    Returns dict with percentile paths and summary stats.
    """
    if len(weekly_returns) < 10:
        return {"error": "Insufficient return history for simulation"}

    arr = np.array(weekly_returns)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr))

    # Simulate paths
    rng = np.random.default_rng(seed=42)
    # Shape: (n_simulations, n_weeks)
    simulated_returns = rng.normal(mu, sigma, size=(n_simulations, n_weeks))

    # Build wealth paths: cumulative product of (1 + r)
    wealth = initial_capital * np.cumprod(1 + simulated_returns, axis=1)

    # Final values
    final_values = wealth[:, -1]

    # Percentile paths (p10, p25, p50, p75, p90) — full time series
    percentiles = [10, 25, 50, 75, 90]
    pct_paths = {}
    for p in percentiles:
        path = np.percentile(wealth, p, axis=0)
        pct_paths[f"p{p}"] = [round(float(v), 2) for v in path]

    # Weekly labels
    weeks = [f"W{i+1}" for i in range(n_weeks)]

    return {
        "weeks": weeks,
        "paths": pct_paths,
        "initial_capital": initial_capital,
        "summary": {
            "mean_final": round(float(np.mean(final_values)), 2),
            "median_final": round(float(np.median(final_values)), 2),
            "p10_final": round(float(np.percentile(final_values, 10)), 2),
            "p90_final": round(float(np.percentile(final_values, 90)), 2),
            "prob_profit": round(float(np.mean(final_values > initial_capital)) * 100, 1),
            "prob_loss_20pct": round(float(np.mean(final_values < initial_capital * 0.8)) * 100, 1),
            "annualized_return_median": round(
                ((float(np.median(final_values)) / initial_capital) ** (52 / n_weeks) - 1) * 100, 2
            ),
            "mu_weekly": round(mu * 100, 4),
            "sigma_weekly": round(sigma * 100, 4),
            "n_simulations": n_simulations,
            "n_weeks": n_weeks,
        },
    }


def compute_portfolio_weekly_returns(
    positions: list[dict],  # [{"ticker": str, "weight": float, "weekly_prices": list[dict]}]
) -> list[float]:
    """
    Compute blended weekly portfolio returns from individual stock histories.
    Uses weighted average of each stock's weekly log returns.
    """
    import pandas as pd

    series_list = []
    weights = []

    for pos in positions:
        prices = pos.get("weekly_prices", [])
        weight = pos.get("weight", 0)
        if len(prices) < 10 or weight <= 0:
            continue
        closes = pd.Series(
            [p["close"] for p in prices],
            index=[p["date"] for p in prices],
        )
        log_returns = np.log(closes / closes.shift(1)).dropna()
        series_list.append(log_returns)
        weights.append(weight)

    if not series_list:
        return []

    # Align on common dates
    df = pd.concat(series_list, axis=1).dropna()
    if df.empty or len(df) < 10:
        return []

    w = np.array(weights)
    w = w / w.sum()  # normalize

    # Weighted portfolio return per week
    portfolio_returns = df.values @ w
    return portfolio_returns.tolist()
