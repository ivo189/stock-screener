---
name: pares-ratio-ibkr
description: VARIANTE IBKR (sin TradingView). Trae los mejores pares (strike largo A / strike corto B) de call ratio spread 1x3 / 1x4 a crédito usando solo el conector de IBKR — universo = watchlist "Opcionables" u otra lista, filtro por cercanía al máximo 52s y volatilidad, cadenas reales y ranking. Usar cuando Ivo pida "los mejores pares con IBKR", "ratio con mi watchlist", o cuando TradingView falle (429). Si pide comparar fuentes, usar también pares-ratio-tv.
---

# Mejores pares de call ratio spread (1xN a crédito) — variante IBKR

Estrategia de Ivo: compro X calls en A, vendo Y > X calls en B > A, vencimiento corto, a **crédito neto**, con (Y−X) calls descubiertos. Criterio: máximo crédito + breakeven superior lo más lejos posible, sobre acciones cerca de un máximo y con volatilidad alta. Responder en español.

Hermano: `pares-ratio-tv` (universo por screener de TradingView). Esta variante probó funcionar de punta a punta el 2026-10-06; sus límites: el universo es el que Ivo tenga en IBKR (no barre el mercado) y el máximo es el de 52 semanas, no el ATH.

## Parámetros (defaults; si Ivo pide otros, aplicarlos y decirlo en una línea)

- Universo: watchlist `Opcionables` (id 106) de IBKR; o la lista de tickers que Ivo dé; o `get_account_positions`.
- Filtros: dist. al máx. 52s ≤ 8% (`high_52w` de `misc_statistics`), vol histórica 30d (`historical-vol.annual_pct`) ≥ 30%, `avg_90d_usd_volume` ≥ USD 300 M.
- Vencimiento: DTE 20–45, de preferencia `trading_class` igual al ticker y sin prefijo numérico (`2AMD`). Si hay earnings antes de ese vencimiento, usar uno anterior al reporte (o excluir el ticker).
- Ratios 3,4 · `--fill natural` · `--min-be-sigma 0.75` · `--min-oi 50` · top 10.

## Paso 1 — Universo y filtro (IBKR)

1. `get_watchlists` → `get_watchlist(id)` devuelve `contract_id_ex` (para acciones es el `underlying_contract_id`). Para tickers fuera de la lista: `search_contracts(query)` y elegir la fila de `symbol` exacto, `country_code` US, con OPT en `sections` (la respuesta es enorme: leer solo esa fila).
2. Por cada ticker, en paralelo: `get_price_snapshot(contract_id, market_data_names=["last","bid_ask","misc_statistics","historical_vol","implied_vol_underlying","avg_90d_usd_volume"])`.
   Claves con guiones: `last.price`, `misc-statistics.high_52w`, `historical-vol.annual_pct` (decimal), `implied-vol-underlying.annual_iv` (decimal), `avg-90d-usd-volume.volume`.
3. dist = last/high_52w − 1 (puede ser positiva si hizo máximo nuevo). Filtrar, y rankear por score = HV% − 3×|dist%|. Mostrar también la IV (si IV ≪ HV, el crédito va a ser flaco).
4. Earnings: IBKR no los trae. Buscar con WebSearch ("<TICKER> next earnings date") o `mcp-tv-get-earnings-calendar` si TradingView responde, y marcar como "estimada" si no es oficial. Calcular `days_to_earnings`.

## Paso 2 — Cadenas (por cada ticker que pasó, máx. ~4)

1. `get_option_parameters(underlying_contract_id)` → elegir el `id` de expiración (verbatim, nunca construirlo).
2. `get_option_data(expiration_id, min_strike=spot, max_strike=spot*1.20)` (la larga puede ser ATM; las ITM no hacen falta). Castear `strike` (viene string). Los strikes se espacian más lejos del spot: no hace falta pedir todos.
3. Por cada call (limitar a ~10–12 strikes): `get_price_snapshot(contract_id=call_contract_id, exchange="SMART", market_data_names=["bid_ask","option_midpoint_iv","option_open_interest"])`, en paralelo. Claves: `bid-ask.bid/ask`, `option-midpoint-iv.annualIv` (decimal ×100 para el CSV), `option-open-interest.callInterest`. Avisar a Ivo cuántas llamadas son antes de lanzarlas.
4. Escribir `chains/TICKER.csv` (`strike,bid,ask,iv,expiry,oi`, expiry `YYYY-MM-DD`) y `meta.tsv` (tabs: `ticker, spot, days_to_earnings, rv21, dist_pct`; poner la HV 30d en `rv21` y decirlo).

Controles: bid ≤ ask, bid decreciente al subir el strike, IV 5–300%. Si el mercado está cerrado, los bid/ask son los últimos cotizados: avisarlo (no ejecutables).

## Paso 3 — Rankear

```bash
python3 .claude/skills/pares-ratio-ibkr/scripts/pares.py --dir chains --meta meta.tsv --top 10 --out pares.csv
```

Parámetros: `--ratios`, `--fill mid`, `--min-credit`, `--min-be-sigma`, `--w-credit`, `--min-oi`, `--allow-earnings`. `ratio_eval.py` es el mismo evaluador que usa el skill `ratio-opciones`.

## Paso 4 — Entrega

1. Título con fecha/hora del dato, fuente (IBKR), universo usado y cuántos tickers pasaron el filtro (y cuáles quedaron afuera con su distancia al máximo).
2. Tabla top 10: #, ticker, venc./DTE, ratio, A/B, crédito (USD por combo), BE sup. (% y σ), prob > BE, margen aprox., P&L +20%.
3. **Recomendación concreta**: par a operar y por qué, una alternativa más conservadora y una más agresiva. Orden sugerida: límite del combo (natural vs mid).
4. Riesgos breves: pérdida ilimitada sobre el BE con (N−1) descubiertos; earnings dentro/cerca del vencimiento; ex-dividendo; nombres pegados al máximo.
5. Aclarar: margen aproximado (verificar con "Check Margin" en TWS), máximo de 52 semanas en vez de ATH, y que no es asesoramiento financiero.

No crear órdenes salvo pedido explícito de Ivo en ese turno (`get_combo_identifier` + `create_order_instruction`, que solo deja la instrucción para revisar en la plataforma).

## Si no hay datos

No inventar precios. Si IBKR no da market data (suscripción/cierre), decirlo y ofrecer un screenshot/CSV de TWS para `ratio-opciones`.
