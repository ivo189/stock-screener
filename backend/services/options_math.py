"""
Matemática pura para el screener de call ratio spreads (sin red, testeable).

Estrategia: comprar `x` calls en el strike bajo A y vender `y` calls en el strike
alto B (B > A, y > x) con crédito neto. Las y - x calls vendidas quedan
descubiertas: la pérdida arriba del breakeven superior es ilimitada.
"""
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

TRADING_DAYS = 252


def realized_vol(closes: list[float], window: int = 21) -> Optional[float]:
    """Vol realizada anualizada en % sobre los últimos `window` retornos log."""
    if len(closes) < window + 1:
        return None
    arr = np.asarray(closes[-(window + 1):], dtype=float)
    if np.any(arr <= 0):
        return None
    lr = np.diff(np.log(arr))
    return float(np.std(lr, ddof=1) * math.sqrt(TRADING_DAYS) * 100)


def biggest_daily_move(closes: list[float], window: int = 21) -> Optional[float]:
    """Mayor retorno diario simple (con signo) en % de las últimas `window` ruedas."""
    if len(closes) < window + 1:
        return None
    arr = np.asarray(closes[-(window + 1):], dtype=float)
    rets = arr[1:] / arr[:-1] - 1
    return float(rets[np.argmax(np.abs(rets))] * 100)


def dist_to_high_pct(close: float, high: float) -> Optional[float]:
    """Distancia al máximo en % (<= 0 cuando está por debajo del máximo)."""
    if not high or high <= 0 or close is None:
        return None
    return (close / high - 1) * 100


def sigma_move_pct(vol_pct: float, days: int) -> float:
    """Movida de 1 desvío estándar en % para `days` ruedas."""
    return vol_pct * math.sqrt(days / TRADING_DAYS)


def underlying_score(vol_pct: float, dist_pct: float, dist_penalty: float = 3.0) -> float:
    """Score = vol - penalidad * |distancia al máximo|. Más alto es mejor."""
    return vol_pct - dist_penalty * abs(dist_pct)


@dataclass
class RatioSpread:
    k_long: float
    k_short: float
    x: int
    y: int
    premium_long: float   # precio por acción de la call comprada
    premium_short: float  # precio por acción de cada call vendida
    multiplier: int = 100

    @property
    def net_credit(self) -> float:
        """Crédito neto por acción (positivo = crédito)."""
        return self.y * self.premium_short - self.x * self.premium_long

    @property
    def naked(self) -> int:
        return self.y - self.x

    @property
    def max_profit(self) -> float:
        """Máxima ganancia por acción: el subyacente termina exactamente en B."""
        return (self.k_short - self.k_long) * self.x + self.net_credit

    @property
    def upper_breakeven(self) -> Optional[float]:
        """Precio sobre el cual empieza la pérdida (solo si hay calls descubiertas)."""
        if self.naked <= 0:
            return None
        return self.k_short + self.max_profit / self.naked

    @property
    def lower_breakeven(self) -> Optional[float]:
        """Debajo del strike largo el resultado es el crédito (si es crédito, no hay pérdida)."""
        if self.net_credit >= 0:
            return None
        return self.k_long - self.net_credit / self.x

    def pnl_at(self, spot: float) -> float:
        """P&L por acción al vencimiento."""
        long_val = self.x * max(spot - self.k_long, 0.0)
        short_val = self.y * max(spot - self.k_short, 0.0)
        return long_val - short_val + self.net_credit

    def payoff_curve(self, lo: float, hi: float, n: int = 60) -> list[dict]:
        pts = []
        for s in np.linspace(lo, hi, n):
            pts.append({"spot": round(float(s), 2),
                        "pnl": round(self.pnl_at(float(s)) * self.multiplier, 2)})
        return pts


def validate_ratio(x: int, y: int) -> None:
    if x < 1 or y <= x:
        raise ValueError("Se requiere y > x >= 1 (más calls vendidas que compradas)")


def mid_price(bid: Optional[float], ask: Optional[float], last: Optional[float] = None) -> Optional[float]:
    """Punto medio bid/ask; cae al último si no hay cotización de ambos lados."""
    if bid and ask and bid > 0 and ask >= bid:
        return (bid + ask) / 2
    if last and last > 0:
        return last
    return None


def conservative_credit(long_ask: float, short_bid: float, x: int, y: int) -> float:
    """Crédito neto 'de pizarra': compro al ask, vendo al bid."""
    return y * short_bid - x * long_ask


def build_spreads(
    calls: list[dict],
    spot: float,
    x: int,
    y: int,
    min_credit: float = 0.0,
    max_otm_long_pct: float = 5.0,
    max_otm_short_pct: float = 25.0,
    min_open_interest: int = 50,
    max_rel_spread: float = 0.35,
) -> list[RatioSpread]:
    """
    Combina strikes de una cadena de calls (dicts con strike, bid, ask, last, oi)
    y devuelve los ratio spreads x:y con crédito neto >= min_credit.

    - Larga: strike entre ~(spot * (1 - max_otm_long_pct)) y spot*(1+max_otm_long_pct)
    - Corta: strike > larga hasta spot * (1 + max_otm_short_pct)
    - Se descartan strikes sin OI suficiente o con bid/ask demasiado ancho.
    """
    validate_ratio(x, y)

    def liquid(c: dict) -> bool:
        bid, ask = c.get("bid") or 0, c.get("ask") or 0
        if ask <= 0 or bid <= 0:
            return False
        if (c.get("oi") or 0) < min_open_interest:
            return False
        return (ask - bid) / ((ask + bid) / 2) <= max_rel_spread

    pool = sorted((c for c in calls if liquid(c)), key=lambda c: c["strike"])
    longs = [c for c in pool
             if spot * (1 - max_otm_long_pct / 100) <= c["strike"] <= spot * (1 + max_otm_long_pct / 100)]
    shorts_all = [c for c in pool if c["strike"] <= spot * (1 + max_otm_short_pct / 100)]

    out: list[RatioSpread] = []
    for lo in longs:
        for sh in shorts_all:
            if sh["strike"] <= lo["strike"]:
                continue
            sp = RatioSpread(
                k_long=lo["strike"], k_short=sh["strike"], x=x, y=y,
                premium_long=mid_price(lo["bid"], lo["ask"], lo.get("last")),
                premium_short=mid_price(sh["bid"], sh["ask"], sh.get("last")),
            )
            if sp.net_credit >= min_credit:
                out.append(sp)
    return out
