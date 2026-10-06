import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import options_math as om


def test_realized_vol_constant_growth_is_zero():
    closes = [100 * 1.01 ** i for i in range(30)]
    assert om.realized_vol(closes, 21) == pytest.approx(0.0, abs=1e-9)


def test_realized_vol_needs_enough_data():
    assert om.realized_vol([1, 2, 3], 21) is None


def test_biggest_move_keeps_sign():
    closes = [100] * 10 + [90] + [91] * 11
    assert om.biggest_daily_move(closes, 21) == pytest.approx(-10.0)


def test_dist_and_sigma():
    assert om.dist_to_high_pct(95, 100) == pytest.approx(-5.0)
    assert om.sigma_move_pct(50, 63) == pytest.approx(25.0)


def test_ratio_1x3_numbers():
    # Compro 1 call 100 @ 5.00, vendo 3 calls 110 @ 2.50 -> crédito 2.50
    sp = om.RatioSpread(100, 110, 1, 3, 5.0, 2.5)
    assert sp.net_credit == pytest.approx(2.5)
    assert sp.naked == 2
    assert sp.max_profit == pytest.approx(12.5)           # 10 + 2.5
    assert sp.upper_breakeven == pytest.approx(116.25)    # 110 + 12.5/2
    assert sp.lower_breakeven is None                     # crédito: sin pérdida abajo
    assert sp.pnl_at(50) == pytest.approx(2.5)
    assert sp.pnl_at(110) == pytest.approx(12.5)
    assert sp.pnl_at(116.25) == pytest.approx(0.0)
    assert sp.pnl_at(130) == pytest.approx(30 - 60 + 2.5)


def test_ratio_validation():
    with pytest.raises(ValueError):
        om.validate_ratio(3, 3)
    with pytest.raises(ValueError):
        om.validate_ratio(2, 1)


def _chain():
    def c(k, bid, ask, oi=500):
        return {"strike": k, "bid": bid, "ask": ask, "last": (bid + ask) / 2, "oi": oi}
    return [c(100, 4.9, 5.1), c(105, 2.9, 3.1), c(110, 1.4, 1.6), c(115, 0.6, 0.8),
            c(120, 0.2, 0.3, oi=5)]  # 120 sin OI -> descartado


def test_build_spreads_filters_and_credit():
    out = om.build_spreads(_chain(), spot=100, x=1, y=3, min_credit=0.0)
    assert out, "debería haber combinaciones a crédito"
    assert all(s.net_credit >= 0 for s in out)
    assert all(s.k_short > s.k_long for s in out)
    assert all(s.k_short != 120 for s in out)  # OI insuficiente


def test_build_spreads_min_credit_excludes_debit():
    out = om.build_spreads(_chain(), spot=100, x=1, y=3, min_credit=10.0)
    assert out == []
