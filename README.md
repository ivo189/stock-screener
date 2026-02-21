# Stock Screener — S&P 500 & DJIA

Screener de acciones del mercado americano. Encuentra oportunidades cercanas al mínimo de 52 semanas con filtros de valuación y crecimiento, y construye portfolios diversificados.

## Requisitos

- Python 3.11+ con **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 22+ con **fnm** (`brew install fnm`)

## Cómo iniciar

### 1. Backend

```bash
./start-backend.sh
# o manualmente:
cd backend && uv run uvicorn main:app --reload
```

Disponible en `http://localhost:8000`
Documentación API interactiva: `http://localhost:8000/docs`

### 2. Frontend (en otra terminal)

```bash
./start-frontend.sh
# o manualmente:
cd frontend && npm run dev
```

Disponible en `http://localhost:5173`

## Funcionamiento

Al iniciar, el backend verifica si hay datos en cache (carpeta `backend/cache/`).
- **Cache vacío:** inicia un fetch de todos los tickers (~10-15 minutos para el S&P500 completo). Los datos se van guardando progresivamente.
- **Cache existente y fresco:** sirve datos inmediatamente.
- **Refresco automático:** todos los días hábiles a las 17:30 ET (22:30 UTC), tras el cierre del mercado.
- **Refresco manual:** botón "Refresh" en la navbar, o `POST /api/screener/refresh`.

## Filtros del Screener

| Filtro | Default | Descripción |
|--------|---------|-------------|
| % sobre mín. 52 semanas | 15% | El precio actual debe estar dentro del X% del mínimo anual |
| P/E máximo | 20x | Ratio precio/ganancia (trailing) |
| EPS CAGR mínimo | 5% | Crecimiento anual compuesto de EPS en los últimos 5 años |
| Dividend Yield mínimo | 2% | Rendimiento por dividendo |

Lógica: (cerca del mín. 52w) **AND** (P/E bajo) **AND** (buen CAGR **OR** buen dividendo)

## Constructor de Portfolio

1. Seleccioná las acciones de oportunidad en la tabla (checkbox)
2. Con 2+ seleccionadas, aparece el botón "Build Portfolio"
3. Elegí método de ponderación:
   - **Risk Parity:** ponderación inversa a la volatilidad (recomendado)
   - **Equal Weight:** 1/N
   - **Market Cap:** proporcional a capitalización
4. Ingresá capital opcional para calcular número de acciones
5. El sistema respeta límites: máx. 15% por acción, máx. 30% por sector

## Estructura del proyecto

```
stock-screener/
├── backend/
│   ├── services/
│   │   ├── data_fetcher.py     # Obtención de datos via yfinance
│   │   ├── screener_service.py # Lógica de filtros y scoring
│   │   ├── portfolio_service.py # Algoritmo de construcción de portfolio
│   │   └── universe.py         # Listas de tickers (S&P500, DJIA)
│   ├── core/
│   │   ├── cache.py            # Cache bicapa (memoria + disco)
│   │   └── scheduler.py        # Refresco diario automático
│   └── api/routes/             # Endpoints FastAPI
└── frontend/
    └── src/
        ├── components/screener/ # Tabla, filtros, charts
        ├── components/portfolio/ # Builder, gráfico de torta
        └── store/               # Estado global (Zustand)
```
