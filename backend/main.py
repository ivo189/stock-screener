import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (ignored by git)
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes.screener import router as screener_router
from api.routes.stocks import router as stocks_router
from api.routes.portfolio import router as portfolio_router
from api.routes.bonds import router as bonds_router
from core.cache import stock_cache
from core.scheduler import start_scheduler, run_full_refresh
from services.bond_service import bond_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Frontend static files path (built React app)
FRONTEND_DIST = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Stock Screener API...")

    # Warm cache from disk
    loaded = stock_cache.warm_from_disk()

    # If cache is stale or empty, trigger a background refresh
    if loaded == 0 or stock_cache.is_stale():
        logger.info("Cache is empty or stale — triggering immediate refresh...")
        import asyncio
        asyncio.create_task(run_full_refresh())
    else:
        logger.info(f"Cache is fresh ({loaded} tickers). Skipping immediate refresh.")

    # Warm bond monitor from disk and trigger initial fetch
    bond_monitor.warm_from_disk()
    import asyncio
    asyncio.create_task(bond_monitor.refresh_all())
    logger.info("Bond monitor initialised; initial price fetch scheduled.")

    # Start the daily scheduler (stocks + bonds)
    start_scheduler()

    yield

    logger.info("Shutting down...")
    from core.scheduler import scheduler
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Stock Screener API",
    description="S&P 500 & DJIA screener — near 52w low, low P/E, EPS CAGR, dividend yield",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend origins: local dev + Vercel deployment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screener_router)
app.include_router(stocks_router)
app.include_router(portfolio_router)
app.include_router(bonds_router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "cache_tickers": len(stock_cache.get_all()),
        "cache_age_seconds": stock_cache.cache_age_seconds(),
        "cache_stale": stock_cache.is_stale(),
    }


# Serve React frontend if built files exist
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend not built")
