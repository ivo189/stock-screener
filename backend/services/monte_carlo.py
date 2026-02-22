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
    Parametric Monte Carlo simulation on portfolio weekly returns.
    weekly_returns: historical weekly total returns (price + dividend), as decimals.
    """
    if len(weekly_returns) < 10:
        return {"error": "Insufficient return history for simulation"}

    arr = np.array(weekly_returns)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr))

    rng = np.random.default_rng(seed=42)
    simulated_returns = rng.normal(mu, sigma, size=(n_simulations, n_weeks))
    wealth = initial_capital * np.cumprod(1 + simulated_returns, axis=1)
    final_values = wealth[:, -1]

    percentiles = [10, 25, 50, 75, 90]
    pct_paths = {}
    for p in percentiles:
        path = np.percentile(wealth, p, axis=0)
        pct_paths[f"p{p}"] = [round(float(v), 2) for v in path]

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


def run_bootstrap(
    weekly_returns: list[float],
    initial_capital: float,
    n_simulations: int = 500,
    n_weeks: int = 52,
) -> dict:
    """
    Historical bootstrap simulation: resamples actual weekly returns instead of
    assuming a normal distribution. Captures fat tails and real market asymmetry.
    """
    if len(weekly_returns) < 10:
        return {"error": "Insufficient return history for bootstrap"}

    arr = np.array(weekly_returns)
    rng = np.random.default_rng(seed=99)

    # Resample with replacement from historical returns
    sampled = rng.choice(arr, size=(n_simulations, n_weeks), replace=True)
    wealth = initial_capital * np.cumprod(1 + sampled, axis=1)
    final_values = wealth[:, -1]

    percentiles = [10, 25, 50, 75, 90]
    pct_paths = {}
    for p in percentiles:
        path = np.percentile(wealth, p, axis=0)
        pct_paths[f"p{p}"] = [round(float(v), 2) for v in path]

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
            "mu_weekly": round(float(np.mean(arr)) * 100, 4),
            "sigma_weekly": round(float(np.std(arr)) * 100, 4),
            "n_simulations": n_simulations,
            "n_weeks": n_weeks,
        },
    }


def compute_portfolio_weekly_returns(
    positions: list[dict],  # [{"ticker", "weight", "weekly_prices", "dividend_yield"}]
) -> list[float]:
    """
    Compute blended weekly portfolio total returns (price + dividend).
    Dividend yield (annual %) is converted to a weekly add-on: div_yield% / 52.
    """
    import pandas as pd

    series_list = []
    weights = []

    for pos in positions:
        prices = pos.get("weekly_prices", [])
        weight = pos.get("weight", 0)
        div_yield_pct = pos.get("dividend_yield") or 0.0  # annual %, e.g. 2.5

        if len(prices) < 10 or weight <= 0:
            continue

        closes = pd.Series(
            [p["close"] for p in prices],
            index=[p["date"] for p in prices],
        )
        # Price return (log)
        log_returns = np.log(closes / closes.shift(1)).dropna()

        # Add weekly dividend contribution: annual_yield% / 52 / 100
        weekly_div = div_yield_pct / 52 / 100
        total_returns = log_returns + weekly_div

        series_list.append(total_returns)
        weights.append(weight)

    if not series_list:
        return []

    df = pd.concat(series_list, axis=1).dropna()
    if df.empty or len(df) < 10:
        return []

    w = np.array(weights)
    w = w / w.sum()

    portfolio_returns = df.values @ w
    return portfolio_returns.tolist()
