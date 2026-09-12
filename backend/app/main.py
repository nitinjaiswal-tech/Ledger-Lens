"""
Ledger Lens — FastAPI Application Entry Point

Run: uvicorn app.main:app --reload (from backend/ directory)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import init_db, AsyncSessionLocal
from .services.data_ingestion import ingest_all
from .api import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}...")
    logger.info(f"Demo Mode: {settings.demo_mode}")
    logger.info(f"Database: {settings.database_url}")

    # Initialize database tables
    await init_db()
    logger.info("Database tables created.")

    # Ingest data (idempotent — skips if already populated)
    async with AsyncSessionLocal() as session:
        result = await ingest_all(session)
        logger.info(f"Data ingestion: {result}")

    logger.info(f"{settings.app_name} ready.")
    yield

    logger.info(f"{settings.app_name} shutting down...")


app = FastAPI(
    title="Ledger Lens API",
    description=(
        "AI-Powered MPLADS Risk Intelligence & Monitoring Platform. "
        "SIH Problem Statement: SIH26102. "
        "AI flags the risk. Evidence explains it. Humans make the decision."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Mount all API routes
app.include_router(api_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": "/api",
        "health": "/api/health",
    }
