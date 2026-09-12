"""API router — aggregates all route modules."""

from fastapi import APIRouter

from .health import router as health_router
from .dashboard import router as dashboard_router
from .projects import router as projects_router, mp_router
from .alerts import router as alerts_router
from .verification import router as verification_router
from .analytics import router as analytics_router
from .investigation import router as investigation_router
from .data_quality import router as data_quality_router

router = APIRouter()

router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(projects_router)
router.include_router(mp_router)
router.include_router(alerts_router)
router.include_router(verification_router)
router.include_router(analytics_router)
router.include_router(investigation_router)
router.include_router(data_quality_router)
