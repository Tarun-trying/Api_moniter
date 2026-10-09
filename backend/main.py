"""
PulseMonitor — FastAPI application entry point (MongoDB Atlas version).
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import connect_db, close_db
from scheduler import start_scheduler, stop_scheduler
from api.monitors import router as monitors_router
from api.checks import router as checks_router
from api.incidents import router as incidents_router
from api.analytics import router as analytics_router


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_start_time = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PulseMonitor starting — connecting to MongoDB Atlas…")
    await connect_db()

    # Start background scheduler (loads monitors from DB)
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    await close_db()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PulseMonitor API",
    description="API monitoring and uptime tracking service",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,https://api-moniter.vercel.app"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(monitors_router)
app.include_router(checks_router)
app.include_router(incidents_router)
app.include_router(analytics_router)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health():
    """Returns service liveness and basic runtime info."""
    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return {
        "status": "ok",
        "service": "PulseMonitor",
        "version": "2.0.0",
        "uptime_seconds": round(uptime_seconds, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "mongodb",
    }
