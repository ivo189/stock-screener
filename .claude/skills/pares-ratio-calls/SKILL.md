---
name: pares-ratio-calls
description: Trae los mejores pares (strike largo A / strike corto B) de call ratio spread 1x3 / 1x4 a crédito, de punta a punta: screener de acciones cerca del máximo con volatilidad alta (TradingView) + cadenas reales de opciones (IBKR) + evaluador. Usar siempre que Ivo pida "los mejores pares", "qué ratio hago hoy", "armame el 1x3", "dame strikes", aunque no nombre el skill.
---

# Mejores pares de call ratio spread (1xN a crédito)

Estrategia de Ivo: compro X calls en A, vendo Y > X calls en B > A, vencimiento corto, a **crédito neto**, con (Y−X) calls descubiertos.
Criterio: máximo crédito + breakeven superior lo más lejos posible, sobre acciones cerca de un máximo y con volatilidad alta.
Responder en español. Esto combina dos skills existentes: `screener-ratio-calls` (subyacentes) y `ratio-opciones` (evaluador). No duplicar su lógica; usar sus pasos y los scripts de `scripts/`.

## Parámetros (defaults; si Ivo pide otros, aplicarlos y decirlo en una línea)

- Subyacentes: top 6 del screener, dist. al ATH ≤ 8%, RV21 ≥ 30%, operado 30d ≥ USD 300 M.
- Vencimiento: el más cercano con DTE entre 20 y 45 (preferir mensual/semanal con `trading_class` igual al ticker, sin prefijo numérico tipo `2NVDA`).
- Ratios 3,4 · `--fill natural` · `--min-be-sigma 0.75` · `--min-oi 50` · top 10 final.
- Earnings antes del vencimiento: se **excluyen** (el gap mata la parte corta). Solo mostrarlos si Ivo pide `--allow-earnings`.

## Paso 1 — Subyacentes

Seguir `screener-ratio-calls` (Ruta A con TradingView; si da 429, esperar 45 s y reintentar hasta 3 veces; si sigue, Ruta B yfinance; si ninguna anda, ver "Si no hay datos"). Quedarse con el top N y guardar en `meta.tsv` (tabs): `ticker, spot, days_to_earnings, rv21, dist_pct`.

Atajo si el screener no está disponible pero IBKR sí: `get_price_snapshot` del subyacente con `misc_statistics`, `historical_vol`, `implied_vol_underlying` da máximos 13/26/52w, vol histórica 30d e IV; sirve para filtrar una lista que Ivo dé (no trae ATH real ni earnings).

## Paso 2 — Cadenas reales con IBKR (por cada ticker del top)

Herramientas del conector `Interactive_Brokers_IBKR` (cargarlas con ToolSearch si no están):

1. `search_contracts(query=TICKER)` → tomar el `underlying_contract_id` de la fila cuyo `symbol` coincide exacto, `country_code` US y `sections` con OPT.
2. `get_price_snapshot(contract_id, market_data_names=["last","bid_ask","implied_vol_underlying"])` → spot (usar `last.price`; si es null, el punto medio de bid/ask).
3. `get_option_parameters(underlying_contract_id)` → elegir la expiración (`id`) con DTE en rango. Usar siempre el `id` verbatim; nunca construirlo. Evitar `trading_class` con prefijo numérico.
4. `get_option_data(expiration_id, min_strike=spot*0.97, max_strike=spot*1.25)` → filas de strikes con `call_contract_id`. Castear `strike` (viene string).
5. Por cada call: `get_price_snapshot(contract_id=call_contract_id, exchange="SMART", market_data_names=["bid_ask","option_midpoint_iv","option_open_interest"])`. Claves de respuesta con guiones: `bid-ask.bid/ask`, `option-midpoint-iv.annualIv` (decimal), `option-open-interest.callInterest`.
   Lanzar en paralelo (tandas de ~8). Son ~10 strikes por ticker; con 6 tickers son ~60 llamadas: avisarlo en una línea antes de empezar.
6. Escribir `chains/TICKER.csv` con columnas `strike,bid,ask,iv,expiry,oi` (expiry `YYYY-MM-DD`). Descartar filas con `isValid=false` o sin bid/ask. Si el mercado está cerrado, bid/ask pueden venir vacíos o congelados: decirlo y marcar que los precios no son ejecutables.

Controles antes de seguir: bid ≤ ask, bid decreciente al subir el strike, IV razonable (5–300%). Si una fila no cuadra, excluirla y decirlo.

## Paso 3 — Rankear

```bash
python3 .claude/skills/pares-ratio-calls/scripts/pares.py --dir chains --meta meta.tsv --top 10 --out pares.csv
```

(Ruta del skill según dónde esté instalado.) `pares.py` usa `ratio_eval.py` (mismo criterio y fórmulas que `ratio-opciones`): crédito, ganancia máxima en K2, breakeven superior en % y σ, prob. de terminar sobre el BE, margen Reg-T aproximado, P&L a +20%, flags `pareto` e `illiquid`. Parámetros útiles: `--ratios`, `--fill mid`, `--min-credit`, `--min-be-sigma`, `--w-credit`, `--min-oi`, `--allow-earnings`.

## Paso 4 — Entrega

1. Título con fecha y hora del dato, fuente (TradingView/yfinance para subyacentes, IBKR para cadenas) y si el mercado estaba abierto.
2. Tabla top 10: #, ticker, venc./DTE, ratio, A/B, crédito (USD por combo), BE sup. (% y σ), prob > BE, margen aprox., P&L +20%, ⚠️ si hay `illiquid`.
3. **Recomendación concreta**: el par a operar y por qué (crédito + distancia), una alternativa más conservadora y una más agresiva, una línea cada una. Orden sugerida: límite del combo (crédito natural vs mid).
4. Riesgos, breves: pérdida ilimitada sobre el BE con (N−1) descubiertos y nivel de ajuste; earnings 22–40 días después (no excluidos pero cercanos); ex-dividendo si B queda ITM; nombres muy extendidos pegados al ATH.
5. Aclarar que el margen es aproximado (verificar con "Check Margin" en TWS) y que no es asesoramiento financiero: la decisión es de Ivo.

No crear órdenes (`create_order_instruction`) salvo que Ivo lo pida explícitamente en este turno; si lo pide, armar el combo con `get_combo_identifier` y mostrar los datos para que él lo revise en la plataforma.

## Si no hay datos

No inventar cierres, IV ni precios de opciones. Decir qué fuente falló (TradingView 429, Yahoo bloqueado, IBKR sin datos de mercado) y ofrecer: reintentar en unos minutos, o que Ivo suba un CSV de TWS / screenshot de la cadena para evaluar con `ratio-opciones`.
