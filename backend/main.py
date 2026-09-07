"""
PulseMonitor — FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
import models  # ensure all ORM models are imported so Base.metadata knows about them
from database import Base
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


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    # Start background scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PulseMonitor API",
    description="API monitoring and uptime tracking service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "PulseMonitor"}
