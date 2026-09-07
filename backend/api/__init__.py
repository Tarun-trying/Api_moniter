from api.monitors import router as monitors_router
from api.checks import router as checks_router
from api.incidents import router as incidents_router
from api.analytics import router as analytics_router

__all__ = ["monitors_router", "checks_router", "incidents_router", "analytics_router"]
