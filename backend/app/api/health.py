"""Health check endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MPAllocation, Project
from ..schemas import HealthResponse
from ..config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check."""
    mp_count = (await db.execute(select(func.count()).select_from(MPAllocation))).scalar() or 0
    proj_count = (await db.execute(select(func.count()).select_from(Project))).scalar() or 0

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        demo_mode=settings.demo_mode,
        database="sqlite" if "sqlite" in settings.database_url else "postgresql",
        mp_records_loaded=mp_count,
        projects_loaded=proj_count,
        timestamp=datetime.utcnow(),
    )
