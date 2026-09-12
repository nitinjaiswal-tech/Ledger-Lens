"""Dashboard summary endpoint."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MPAllocation, Project, RiskScore, VerificationCase, VerificationStatus
from ..schemas import DashboardSummary, RiskDistribution, StateRiskSummary
from ..config import get_settings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
settings = get_settings()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Main dashboard KPI summary."""

    # MP allocation stats
    total_mp = (await db.execute(select(func.count()).select_from(MPAllocation))).scalar() or 0
    total_allocation = (
        await db.execute(select(func.sum(MPAllocation.allocated_amount_inr)))
    ).scalar() or 0.0
    financial_outliers = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_financial_outlier == True)
        )
    ).scalar() or 0
    dq_issues = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_data_quality_issue == True)
        )
    ).scalar() or 0

    # Project stats
    total_projects = (await db.execute(select(func.count()).select_from(Project))).scalar() or 0
    total_expenditure = (
        await db.execute(select(func.sum(Project.expenditure_amount)))
    ).scalar() or 0.0

    critical_count = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.risk_level == "CRITICAL")
        )
    ).scalar() or 0
    high_count = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.risk_level == "HIGH")
        )
    ).scalar() or 0
    moderate_count = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.risk_level == "MODERATE")
        )
    ).scalar() or 0
    low_count = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.risk_level == "LOW")
        )
    ).scalar() or 0

    delayed = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.delay_days > 90)
        )
    ).scalar() or 0

    requiring_verification = (
        await db.execute(
            select(func.count()).select_from(VerificationCase).where(
                VerificationCase.status.in_(["AI_FLAGGED", "UNDER_REVIEW"])
            )
        )
    ).scalar() or 0

    return DashboardSummary(
        total_mp_records=total_mp,
        total_projects=total_projects,
        total_sanctioned_amount=float(total_allocation),
        total_expenditure=float(total_expenditure),
        high_risk_count=high_count,
        critical_risk_count=critical_count,
        moderate_risk_count=moderate_count,
        low_risk_count=low_count,
        projects_requiring_verification=requiring_verification,
        delayed_projects=delayed,
        financial_outliers=financial_outliers,
        data_quality_issues=dq_issues,
        demo_mode=settings.demo_mode,
        data_source_label="OFFICIAL DATA (MP Allocations) + SYNTHETIC DEMO (Projects)" if settings.demo_mode else "OFFICIAL DATA",
        last_updated=datetime.utcnow(),
    )


@router.get("/risk-distribution", response_model=List[RiskDistribution])
async def get_risk_distribution(db: AsyncSession = Depends(get_db)):
    """Risk level distribution for projects."""
    total = (await db.execute(select(func.count()).select_from(Project))).scalar() or 1

    tiers = [
        ("CRITICAL", "#dc2626"),
        ("HIGH", "#ea580c"),
        ("MODERATE", "#d97706"),
        ("LOW", "#16a34a"),
    ]

    result = []
    for level, color in tiers:
        count = (
            await db.execute(
                select(func.count()).select_from(Project).where(Project.risk_level == level)
            )
        ).scalar() or 0
        result.append(RiskDistribution(
            risk_level=level,
            count=count,
            percentage=round(count / total * 100, 1),
            color=color,
        ))
    return result


from sqlalchemy import select, func, case, literal

@router.get("/state-risk", response_model=List[StateRiskSummary])
@router.get("/state-summary", response_model=List[StateRiskSummary])
async def get_state_risk_summary(db: AsyncSession = Depends(get_db)):
    """Risk summary by state from MP allocation data."""
    stmt = (
        select(
            MPAllocation.state,
            func.count(MPAllocation.id).label("total_records"),
            func.avg(MPAllocation.anomaly_score).label("avg_anomaly_score"),
            func.sum(MPAllocation.allocated_amount_inr).label("total_allocation"),
            func.sum(case((MPAllocation.is_financial_outlier == True, literal(1)), else_=literal(0))).label("critical_count"),
        )
        .group_by(MPAllocation.state)
        .order_by(func.avg(MPAllocation.anomaly_score).desc())
    )
    rows = (await db.execute(stmt)).all()

    result = []
    for row in rows:
        result.append(StateRiskSummary(
            state=row.state,
            total_records=row.total_records,
            avg_risk_score=round(float(row.avg_anomaly_score or 0), 1),
            critical_count=int(row.critical_count or 0),
            high_count=0,
            total_allocation=float(row.total_allocation or 0),
        ))
    return result
