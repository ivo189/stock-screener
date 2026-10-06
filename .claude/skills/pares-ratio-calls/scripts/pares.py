#!/usr/bin/env python3
"""Ranking global de call ratio spreads 1xN entre varios subyacentes.

Entrada: una carpeta con TICKER.csv (strike,bid,ask,iv,expiry[,oi]) por subyacente y un meta.tsv
con columnas: ticker, spot, days_to_earnings (opcional), rv21 (opcional), dist_pct (opcional).
Reutiliza ratio_eval.py (evaluate/rank) para que el criterio sea el mismo que el del skill ratio-opciones.

Uso: python pares.py --dir chains --meta meta.tsv [--ratios 3,4] [--fill natural] [--min-credit 0]
        [--min-be-sigma 0.75] [--w-credit 0.5] [--min-oi 50] [--top 10] [--out pares.csv]
"""
import argparse, csv, os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ratio_eval as re_


def load_meta(path):
    meta = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            meta[r["ticker"].strip().upper()] = r
    return meta


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--meta", required=True)
    ap.add_argument("--ratios", default="3,4"); ap.add_argument("--fill", default="natural", choices=["natural", "mid"])
    ap.add_argument("--rate", type=float, default=0.04); ap.add_argument("--min-credit", type=float, default=0.0)
    ap.add_argument("--min-be-sigma", type=float, default=0.75); ap.add_argument("--w-credit", type=float, default=0.5)
    ap.add_argument("--min-oi", type=int, default=50, help="open interest minimo por strike (si el CSV trae oi)")
    ap.add_argument("--allow-earnings", action="store_true", help="no marcar/excluir combos con earnings antes del venc.")
    ap.add_argument("--top", type=int, default=10); ap.add_argument("--out")
    a = ap.parse_args()
    ratios = [int(x) for x in a.ratios.split(",")]
    meta = load_meta(a.meta)

    allrows = []
    for tk, m in meta.items():
        path = os.path.join(a.dir, f"{tk}.csv")
        spot = num(m.get("spot"))
        if not os.path.exists(path) or not spot:
            print(f"# {tk}: sin cadena o sin spot, se omite", file=sys.stderr); continue
        chain = re_.load_chain(path)
        oi = {}
        with open(path, newline="", encoding="utf-8-sig") as f:   # OI no lo lee load_chain
            for r in csv.DictReader(f):
                oi[(r.get("expiry", ""), float(r["strike"]))] = num(r.get("oi")) or 0
        chain = [c for c in chain if oi.get((c["expiry"], c["strike"]), a.min_oi) >= a.min_oi]
        groups = {}
        for c in chain: groups.setdefault(c["expiry"], []).append(c)
        dte_earn = num(m.get("days_to_earnings"))
        for exp, ch in groups.items():
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days
            if dte < 1: continue
            T = dte / 365
            rows, atm_iv, sd = re_.evaluate(ch, spot, T, a.rate, ratios, a.fill, a.min_credit, a.min_be_sigma)
            for r in rows:
                r.update(ticker=tk, expiry=exp, dte=dte, spot=spot, iv_atm=round(atm_iv * 100, 1),
                         rv21=m.get("rv21", ""), dist_ath=m.get("dist_pct", ""),
                         earnings_antes="SI" if dte_earn is not None and 0 <= dte_earn <= dte else "")
            allrows += rows

    if not a.allow_earnings:
        dropped = sum(1 for r in allrows if r["earnings_antes"])
        allrows = [r for r in allrows if not r["earnings_antes"]]
        if dropped: print(f"# {dropped} combos descartados por earnings antes del vencimiento (--allow-earnings para verlos)")

    ranked = re_.rank(allrows, a.w_credit)
    cols = ["score", "ticker", "expiry", "dte", "N", "K1", "K2", "spot", "credit_usd", "max_profit_usd", "short_otm_pct",
            "be_up", "be_up_pct", "be_up_sigma", "p_above_be", "margin_regt_usd", "ret_on_margin_pct",
            "pnl_+20%", "iv_atm", "rv21", "dist_ath", "pareto", "illiquid"]
    print(",".join(cols))
    for r in ranked[:a.top]: print(",".join(str(r.get(c, "")) for c in cols))
    if a.out and ranked:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ranked[0].keys())); w.writeheader(); w.writerows(ranked)
        print(f"# ranking completo -> {a.out}")
    if not ranked: print("# Ningun combo cumple los filtros. Probar --min-be-sigma menor, --min-credit negativo o --fill mid.")


if __name__ == "__main__":
    main()
