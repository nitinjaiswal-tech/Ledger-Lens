"""Data quality API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MPAllocation
from ..schemas import DataQualitySummary

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/summary", response_model=DataQualitySummary)
async def get_data_quality_summary(db: AsyncSession = Depends(get_db)):
    """Data quality summary for MP allocation records."""
    total = (await db.execute(select(func.count()).select_from(MPAllocation))).scalar() or 1
    missing = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_missing_amount == True)
        )
    ).scalar() or 0
    invalid = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_invalid_amount == True)
        )
    ).scalar() or 0
    duplicate = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_duplicate_constituency == True)
        )
    ).scalar() or 0
    outliers = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_financial_outlier == True)
        )
    ).scalar() or 0
    issues = (
        await db.execute(
            select(func.count()).select_from(MPAllocation).where(MPAllocation.is_data_quality_issue == True)
        )
    ).scalar() or 0

    # Quality score: deduct for missing, invalid, duplicate
    penalty = (missing * 10 + invalid * 20 + duplicate * 5) / total * 100
    score = max(0.0, min(100.0, 100.0 - penalty))

    if score >= 95:
        label = "Excellent"
    elif score >= 85:
        label = "Good"
    elif score >= 70:
        label = "Acceptable"
    else:
        label = "Needs Attention"

    return DataQualitySummary(
        total_mp_records=total,
        missing_amounts=missing,
        invalid_amounts=invalid,
        duplicate_constituencies=duplicate,
        financial_outliers=outliers,
        data_quality_score=round(score, 1),
        data_quality_label=label,
        methodology_note=(
            "Data Quality Score deducts points for missing amounts (10pt), "
            "invalid amounts (20pt), and duplicate constituency records (5pt) "
            "relative to total MP records. This is a demonstration metric, "
            "not an official government quality standard."
        ),
    )


@router.get("/issues")
async def get_data_quality_issues(db: AsyncSession = Depends(get_db)):
    """List records with data quality issues."""
    result = await db.execute(
        select(MPAllocation).where(MPAllocation.is_data_quality_issue == True)
    )
    issues = result.scalars().all()

    return [
        {
            "id": r.id,
            "sr_no": r.sr_no,
            "mp_name": r.mp_name,
            "state": r.state,
            "constituency": r.constituency_clean,
            "allocated_amount_inr": r.allocated_amount_inr,
            "issues": [
                *( ["Missing Amount"] if r.is_missing_amount else []),
                *( ["Invalid Amount"] if r.is_invalid_amount else []),
                *( ["Duplicate Constituency"] if r.is_duplicate_constituency else []),
            ],
            "anomaly_score": r.anomaly_score,
        }
        for r in issues
    ]
