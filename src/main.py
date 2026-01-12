import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.config import settings
from src.database.connection import init_db
from src.api.inspections import router as inspections_router
from src.api.dashboard import router as dashboard_router
from src.api.crm import router as crm_router
from src.services.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with error handling."""
    # Startup
    logger.info("Starting OSHA Tracker application...")

    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    try:
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        # Continue without scheduler if it fails
        logger.warning("Application running without background scheduler")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down OSHA Tracker application...")

    try:
        stop_scheduler()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    logger.info("Application shutdown complete")


app = FastAPI(
    title="OSHA Tracker",
    description="Monitor OSHA inspections and enrich with contact data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to set CSP headers for dashboard JavaScript
class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Allow inline scripts and styles for the dashboard
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://cdn.jsdelivr.net"
        )
        return response

app.add_middleware(CSPMiddleware)

# API routes
app.include_router(inspections_router, prefix="/api/inspections", tags=["inspections"])
app.include_router(crm_router, prefix="/api/crm", tags=["crm"])
app.include_router(dashboard_router, tags=["dashboard"])

# Serve static files for dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "osha-tracker"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
