#!/usr/bin/env python3
"""Evaluador de call ratio spreads 1xN (compro 1 call K1, vendo N calls K2>K1).

Uso:
  python ratio_eval.py chain.csv --spot 45.20 [--expiry 2026-10-16 | --dte 22]
         [--ratios 3,4] [--fill natural|mid] [--rate 0.04] [--min-credit 0]
         [--min-be-sigma 0.75] [--allow-itm-short] [--w-credit 0.5] [--top 15] [--out ranking.csv]

CSV (una fila por strike de CALL; columnas extra se ignoran):
  strike,bid,ask[,iv][,delta][,expiry][,right]
  - iv en % (32.5) o decimal (0.325). Si falta se calcula del mid con Black-Scholes.
  - si hay columna expiry (YYYY-MM-DD) se evalua cada vencimiento por separado.
  - si hay columna right, solo se usan filas C/CALL.
Solo stdlib.
"""
import argparse, csv, math, sys
from datetime import date, datetime

# ---------- Black-Scholes ----------
def _ncdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def bs_call(S, K, T, r, v):
    if T <= 0 or v <= 0: return max(S - K, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T))
    return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d1 - v * math.sqrt(T))

def bs_delta(S, K, T, r, v):
    if T <= 0 or v <= 0: return 1.0 if S > K else 0.0
    return _ncdf((math.log(S / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T)))

def implied_vol(price, S, K, T, r):
    if price <= max(S - K * math.exp(-r * T), 0) + 1e-6: return None
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if bs_call(S, K, T, r, mid) > price: hi = mid
        else: lo = mid
    return (lo + hi) / 2

def prob_above(S, X, T, r, v):
    """P(S_T > X) bajo lognormal con vol v."""
    if X <= 0: return 1.0
    d2 = (math.log(S / X) + (r - 0.5 * v * v) * T) / (v * math.sqrt(T))
    return _ncdf(d2)

# ---------- Estructura ----------
def payoff(S_T, K1, K2, N, credit):
    """P&L por accion al vencimiento (credit>0 = cobro neto)."""
    return credit + max(S_T - K1, 0) - N * max(S_T - K2, 0)

def regt_naked_call(S, K, prem):
    """Margen Reg-T por accion de un call vendido descubierto (aprox. IBKR)."""
    otm = max(K - S, 0)
    return max(0.20 * S - otm, 0.10 * S) + prem

def load_chain(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        rd.fieldnames = [c.strip().lower() for c in rd.fieldnames]
        for r in rd:
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            if r.get("right") and r["right"].upper()[0] != "C": continue
            try:
                row = {"strike": float(r["strike"]), "bid": float(r["bid"] or 0), "ask": float(r["ask"] or 0)}
            except (KeyError, ValueError):
                continue
            if r.get("iv"):
                iv = float(r["iv"].replace("%", "")); row["iv"] = iv / 100 if iv > 3 else iv
            if r.get("delta"): row["delta"] = float(r["delta"])
            row["expiry"] = r.get("expiry") or ""
            rows.append(row)
    return rows

def evaluate(chain, S, T, r, ratios, fill, min_credit, min_be_sigma=0.0, allow_itm_short=False):
    chain = sorted(chain, key=lambda x: x["strike"])
    for c in chain:
        c["mid"] = (c["bid"] + c["ask"]) / 2 if c["ask"] > 0 else c["bid"]
        if "iv" not in c:
            c["iv"] = implied_vol(c["mid"], S, c["strike"], T, r) if c["mid"] > 0 else None
        if "delta" not in c and c["iv"]:
            c["delta"] = bs_delta(S, c["strike"], T, r, c["iv"])
    atm = min(chain, key=lambda c: abs(c["strike"] - S))
    atm_iv = atm["iv"] or next((c["iv"] for c in chain if c["iv"]), 0.3)
    sd = atm_iv * math.sqrt(T)  # 1 sigma en log-precio
    out = []
    for i, L in enumerate(chain):
        buy = L["ask"] if fill == "natural" else L["mid"]
        if buy <= 0: continue
        for Sh in chain[i + 1:]:
            sell = Sh["bid"] if fill == "natural" else Sh["mid"]
            if sell <= 0 or Sh["bid"] <= 0: continue
            K1, K2 = L["strike"], Sh["strike"]
            if K2 <= S and not allow_itm_short: continue
            for N in ratios:
                credit = N * sell - buy
                if credit < min_credit: continue
                width = K2 - K1
                max_profit = credit + width
                be_up = K2 + max_profit / (N - 1)
                if math.log(be_up / S) / sd < min_be_sigma: continue
                be_dn = K1 - credit if credit < 0 else None
                naked = N - 1
                margin = naked * regt_naked_call(S, K2, Sh["bid"]) * 100
                spread_pct = lambda c: (c["ask"] - c["bid"]) / c["mid"] if c["mid"] > 0 else 9
                out.append({
                    "expiry": L.get("expiry", ""), "N": N, "K1": K1, "K2": K2,
                    "buy_px": round(buy, 3), "sell_px": round(sell, 3),
                    "credit_usd": round(credit * 100, 2),
                    "max_profit_usd": round(max_profit * 100, 2),
                    "short_otm_pct": round((K2 / S - 1) * 100, 2),
                    "short_delta": round(Sh.get("delta") or 0, 3),
                    "be_up": round(be_up, 2),
                    "be_up_pct": round((be_up / S - 1) * 100, 2),
                    "be_up_sigma": round(math.log(be_up / S) / sd, 2),
                    "be_dn": round(be_dn, 2) if be_dn else "",
                    "p_above_be": round(prob_above(S, be_up, T, r, Sh["iv"] or atm_iv) * 100, 1),
                    "p_above_K2": round(prob_above(S, K2, T, r, Sh["iv"] or atm_iv) * 100, 1),
                    "net_delta": round(((L.get("delta") or 0) - N * (Sh.get("delta") or 0)) * 100, 1),
                    "margin_regt_usd": round(margin, 0),
                    "ret_on_margin_pct": round(credit * 100 / margin * 100, 2) if margin else 0,
                    "pnl_+10%": round(payoff(S * 1.10, K1, K2, N, credit) * 100, 0),
                    "pnl_+20%": round(payoff(S * 1.20, K1, K2, N, credit) * 100, 0),
                    "pnl_+2sd": round(payoff(S * math.exp(2 * sd), K1, K2, N, credit) * 100, 0),
                    "illiquid": "SI" if max(spread_pct(L), spread_pct(Sh)) > 0.25 else "",
                })
    return out, atm_iv, sd

def rank(rows, w_credit):
    if not rows: return rows
    # Frontera de Pareto: nadie tiene mas credito Y breakeven mas lejano
    for a in rows:
        a["pareto"] = "" if any(b["credit_usd"] >= a["credit_usd"] and b["be_up_sigma"] >= a["be_up_sigma"]
                                and (b["credit_usd"] > a["credit_usd"] or b["be_up_sigma"] > a["be_up_sigma"])
                                for b in rows) else "*"
    cmax = max(r["credit_usd"] for r in rows) or 1
    cmin = min(r["credit_usd"] for r in rows)
    smax = max(r["be_up_sigma"] for r in rows); smin = min(r["be_up_sigma"] for r in rows)
    for r in rows:
        nc = (r["credit_usd"] - cmin) / (cmax - cmin) if cmax > cmin else 1
        ns = (r["be_up_sigma"] - smin) / (smax - smin) if smax > smin else 1
        # media geometrica ponderada: castiga combos que son buenos en una sola dimension
        base = (max(nc, 0.01) ** w_credit) * (max(ns, 0.01) ** (1 - w_credit))
        r["score"] = round(100 * base - (10 if r["illiquid"] else 0), 1)
    return sorted(rows, key=lambda r: (-r["score"], -r["credit_usd"]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--spot", type=float, required=True)
    ap.add_argument("--expiry"); ap.add_argument("--dte", type=float)
    ap.add_argument("--ratios", default="3,4"); ap.add_argument("--fill", default="natural", choices=["natural", "mid"])
    ap.add_argument("--rate", type=float, default=0.04); ap.add_argument("--min-credit", type=float, default=0.0,
                    help="credito neto minimo por accion (0 = solo credito o costo cero)")
    ap.add_argument("--w-credit", type=float, default=0.5, help="peso del credito en el score (resto = distancia)")
    ap.add_argument("--min-be-sigma", type=float, default=0.75, help="breakeven superior minimo en sigmas")
    ap.add_argument("--allow-itm-short", action="store_true", help="permitir vender strikes <= spot")
    ap.add_argument("--top", type=int, default=15); ap.add_argument("--out")
    a = ap.parse_args()
    ratios = [int(x) for x in a.ratios.split(",")]
    chain = load_chain(a.csv)
    groups = {}
    for c in chain: groups.setdefault(c["expiry"] or a.expiry or "", []).append(c)
    allrows = []
    for exp, ch in groups.items():
        if a.dte is not None and not exp: dte = a.dte
        elif exp: dte = (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days
        else: sys.exit("Falta --expiry o --dte (o columna expiry en el CSV)")
        T = max(dte, 0.5) / 365
        rows, atm_iv, sd = evaluate(ch, a.spot, T, a.rate, ratios, a.fill, a.min_credit, a.min_be_sigma, a.allow_itm_short)
        for r in rows: r["expiry"] = exp; r["dte"] = dte
        print(f"# {exp or 'venc.'}  DTE={dte}  spot={a.spot}  IV ATM={atm_iv*100:.1f}%  1σ al venc.={sd*100:.1f}%  combos={len(rows)}")
        allrows += rows
    ranked = rank(allrows, a.w_credit)
    cols = ["score", "pareto", "expiry", "N", "K1", "K2", "credit_usd", "max_profit_usd", "short_otm_pct", "short_delta",
            "be_up", "be_up_pct", "be_up_sigma", "p_above_be", "net_delta", "margin_regt_usd", "ret_on_margin_pct",
            "pnl_+10%", "pnl_+20%", "pnl_+2sd", "illiquid"]
    print(",".join(cols))
    for r in ranked[:a.top]: print(",".join(str(r[c]) for c in cols))
    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ranked[0].keys()) if ranked else cols); w.writeheader(); w.writerows(ranked)
        print(f"# ranking completo -> {a.out}")
    if not ranked: print("# Ningun combo cumple los filtros. Probar --min-credit negativo, --min-be-sigma menor o --fill mid.")

if __name__ == "__main__":
    main()
