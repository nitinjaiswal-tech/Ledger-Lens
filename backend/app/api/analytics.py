"""Analytics API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MPAllocation, Project, RiskScore
from ..schemas import DataQualitySummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/risk")
async def get_risk_analytics(db: AsyncSession = Depends(get_db)):
    """Risk analytics overview."""
    # Risk by state (from projects)
    state_risk = await db.execute(
        select(
            Project.state,
            func.count(Project.id).label("count"),
            func.avg(Project.risk_score).label("avg_risk"),
            func.sum(func.cast(Project.risk_level == "CRITICAL", type_=None)).label("critical"),
            func.sum(func.cast(Project.risk_level == "HIGH", type_=None)).label("high"),
        ).group_by(Project.state).order_by(func.avg(Project.risk_score).desc())
    )
    state_rows = state_risk.all()

    # Risk by category
    cat_risk = await db.execute(
        select(
            Project.work_category,
            func.count(Project.id).label("count"),
            func.avg(Project.risk_score).label("avg_risk"),
        ).group_by(Project.work_category).order_by(func.avg(Project.risk_score).desc()).limit(15)
    )
    cat_rows = cat_risk.all()

    # Risk by implementing agency
    agency_risk = await db.execute(
        select(
            Project.implementing_agency,
            func.count(Project.id).label("count"),
            func.avg(Project.risk_score).label("avg_risk"),
        ).group_by(Project.implementing_agency).order_by(func.avg(Project.risk_score).desc()).limit(10)
    )
    agency_rows = agency_risk.all()

    return {
        "by_state": [
            {
                "state": r.state,
                "count": r.count,
                "avg_risk_score": round(float(r.avg_risk or 0), 1),
                "critical_count": int(r.critical or 0),
                "high_count": int(r.high or 0),
            }
            for r in state_rows
        ],
        "by_category": [
            {
                "category": r.work_category,
                "count": r.count,
                "avg_risk_score": round(float(r.avg_risk or 0), 1),
            }
            for r in cat_rows
        ],
        "by_agency": [
            {
                "agency": r.implementing_agency,
                "count": r.count,
                "avg_risk_score": round(float(r.avg_risk or 0), 1),
            }
            for r in agency_rows
        ],
    }


@router.get("/financial")
async def get_financial_analytics(db: AsyncSession = Depends(get_db)):
    """Financial analytics from MP allocation data (REAL data)."""
    total = (await db.execute(select(func.count()).select_from(MPAllocation))).scalar() or 0
    total_amount = (await db.execute(select(func.sum(MPAllocation.allocated_amount_inr)))).scalar() or 0.0
    avg_amount = (await db.execute(select(func.avg(MPAllocation.allocated_amount_inr)))).scalar() or 0.0
    max_amount = (await db.execute(select(func.max(MPAllocation.allocated_amount_inr)))).scalar() or 0.0
    min_amount = (await db.execute(
        select(func.min(MPAllocation.allocated_amount_inr)).where(MPAllocation.allocated_amount_inr > 0)
    )).scalar() or 0.0

    # By state
    state_stats = await db.execute(
        select(
            MPAllocation.state,
            func.count(MPAllocation.id).label("mp_count"),
            func.sum(MPAllocation.allocated_amount_inr).label("total_allocation"),
            func.avg(MPAllocation.allocated_amount_inr).label("avg_allocation"),
            func.avg(MPAllocation.anomaly_score).label("avg_anomaly"),
        ).group_by(MPAllocation.state).order_by(func.sum(MPAllocation.allocated_amount_inr).desc())
    )
    state_rows = state_stats.all()

    # Top outliers
    outlier_result = await db.execute(
        select(MPAllocation)
        .where(MPAllocation.is_financial_outlier == True)
        .order_by(MPAllocation.anomaly_score.desc())
        .limit(10)
    )
    outliers = outlier_result.scalars().all()

    return {
        "summary": {
            "total_mps": total,
            "total_allocation_inr": float(total_amount),
            "avg_allocation_inr": float(avg_amount),
            "max_allocation_inr": float(max_amount),
            "min_allocation_inr": float(min_amount),
            "data_source": "OFFICIAL DATA — Real MP Allocations (18th Lok Sabha)",
        },
        "by_state": [
            {
                "state": r.state,
                "mp_count": r.mp_count,
                "total_allocation_inr": float(r.total_allocation or 0),
                "avg_allocation_inr": float(r.avg_allocation or 0),
                "avg_anomaly_score": round(float(r.avg_anomaly or 0), 1),
            }
            for r in state_rows
        ],
        "financial_outliers": [
            {
                "mp_name": o.mp_name,
                "state": o.state,
                "constituency": o.constituency_clean,
                "allocated_amount_inr": o.allocated_amount_inr,
                "anomaly_score": o.anomaly_score,
                "allocation_zscore": o.allocation_zscore,
                "state_peer_deviation_pct": o.state_peer_deviation_pct,
            }
            for o in outliers
        ],
    }


@router.get("/progress")
async def get_progress_analytics(db: AsyncSession = Depends(get_db)):
    """Progress analytics from demo project data."""
    # Status distribution
    status_dist = await db.execute(
        select(Project.status, func.count(Project.id).label("count"))
        .group_by(Project.status)
    )
    status_rows = status_dist.all()

    # Avg metrics
    avg_metrics = await db.execute(
        select(
            func.avg(Project.physical_progress_pct).label("avg_progress"),
            func.avg(Project.utilization_ratio).label("avg_utilization"),
            func.avg(Project.delay_days).label("avg_delay"),
            func.avg(Project.payment_progress_gap).label("avg_gap"),
        )
    )
    metrics = avg_metrics.one()

    # High gap projects count
    mismatch_count = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.payment_progress_gap > 30)
        )
    ).scalar() or 0

    return {
        "status_distribution": [
            {"status": str(r.status.value if hasattr(r.status, 'value') else r.status), "count": r.count}
            for r in status_rows
        ],
        "avg_physical_progress_pct": round(float(metrics.avg_progress or 0), 1),
        "avg_utilization_ratio": round(float(metrics.avg_utilization or 0), 3),
        "avg_delay_days": round(float(metrics.avg_delay or 0), 0),
        "avg_payment_progress_gap": round(float(metrics.avg_gap or 0), 1),
        "payment_mismatch_count": mismatch_count,
        "note": "SYNTHETIC DEMO DATA — project progress records are not from official eSAKSHI export",
    }
