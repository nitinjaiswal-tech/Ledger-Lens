"""Investigation assistant API — constrained query over actual database records."""

from typing import Optional
from fastapi import APIRouter, Depends, Body
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Project, MPAllocation

router = APIRouter(prefix="/investigation", tags=["Investigation"])


@router.post("/query")
async def investigation_query(
    question: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Constrained investigation assistant that queries actual database records.

    Answers questions about risk patterns, project data, and anomalies.
    All answers are backed by real database records.
    No hallucinated figures.
    """
    question_lower = question.lower()

    # ─── Critical risk projects ───────────────────────────────────────────────
    if any(k in question_lower for k in ["critical", "most risky", "highest risk"]):
        result = await db.execute(
            select(Project)
            .where(Project.risk_level == "CRITICAL")
            .order_by(Project.risk_score.desc())
            .limit(5)
        )
        projects = result.scalars().all()

        if not projects:
            return {"answer": "No critical-risk projects found in the current dataset.", "records": []}

        records = [
            {
                "project_id": p.project_id,
                "description": p.work_description[:80],
                "state": p.state,
                "risk_score": p.risk_score,
                "risk_level": str(p.risk_level.value if hasattr(p.risk_level, 'value') else p.risk_level),
            }
            for p in projects
        ]
        return {
            "answer": f"Found {len(projects)} critical-risk projects. Top projects are shown below.",
            "records": records,
            "source": "Ledger Lens project risk database (SYNTHETIC DEMO)",
        }

    # ─── Payment-progress mismatch ────────────────────────────────────────────
    elif any(k in question_lower for k in ["payment", "mismatch", "expenditure", "progress"]):
        result = await db.execute(
            select(Project)
            .where(Project.payment_progress_gap > 30)
            .order_by(Project.payment_progress_gap.desc())
            .limit(5)
        )
        projects = result.scalars().all()
        count = (
            await db.execute(
                select(func.count()).select_from(Project).where(Project.payment_progress_gap > 30)
            )
        ).scalar() or 0

        if not projects:
            return {"answer": "No significant payment-progress mismatches found.", "records": []}

        records = [
            {
                "project_id": p.project_id,
                "state": p.state,
                "financial_progress_pct": p.financial_progress_pct,
                "physical_progress_pct": p.physical_progress_pct,
                "payment_progress_gap": p.payment_progress_gap,
                "risk_level": str(p.risk_level.value if hasattr(p.risk_level, 'value') else p.risk_level),
            }
            for p in projects
        ]
        return {
            "answer": (
                f"Found {count} projects with payment-progress gap above 30 percentage points. "
                "These show higher financial utilization than physical progress — a pattern that requires verification."
            ),
            "records": records,
            "source": "Ledger Lens project database (SYNTHETIC DEMO)",
        }

    # ─── Delayed projects ─────────────────────────────────────────────────────
    elif any(k in question_lower for k in ["delay", "delayed", "late", "overdue"]):
        result = await db.execute(
            select(Project)
            .where(Project.delay_days > 90)
            .order_by(Project.delay_days.desc())
            .limit(5)
        )
        projects = result.scalars().all()
        count = (
            await db.execute(
                select(func.count()).select_from(Project).where(Project.delay_days > 90)
            )
        ).scalar() or 0

        records = [
            {
                "project_id": p.project_id,
                "state": p.state,
                "district": p.district,
                "delay_days": p.delay_days,
                "status": str(p.status.value if hasattr(p.status, 'value') else p.status),
                "risk_score": p.risk_score,
            }
            for p in projects
        ]
        return {
            "answer": f"Found {count} delayed projects (delay > 90 days). Top 5 most delayed shown below.",
            "records": records,
            "source": "Ledger Lens project database (SYNTHETIC DEMO)",
        }

    # ─── Financial outliers ───────────────────────────────────────────────────
    elif any(k in question_lower for k in ["outlier", "unusual", "anomal", "allocation"]):
        result = await db.execute(
            select(MPAllocation)
            .where(MPAllocation.is_financial_outlier == True)
            .order_by(MPAllocation.anomaly_score.desc())
            .limit(5)
        )
        mps = result.scalars().all()
        count = (
            await db.execute(
                select(func.count()).select_from(MPAllocation).where(MPAllocation.is_financial_outlier == True)
            )
        ).scalar() or 0

        records = [
            {
                "mp_name": m.mp_name,
                "state": m.state,
                "constituency": m.constituency_clean,
                "allocated_amount_inr": m.allocated_amount_inr,
                "anomaly_score": m.anomaly_score,
                "zscore": m.allocation_zscore,
            }
            for m in mps
        ]
        return {
            "answer": (
                f"Found {count} MP allocations flagged as financial outliers by the Isolation Forest model. "
                "These are statistically unusual compared to the national and state distributions. "
                "This is an Anomaly Signal — NOT an indication of wrongdoing."
            ),
            "records": records,
            "source": "Ledger Lens MP Allocation database (OFFICIAL DATA)",
        }

    # ─── State risk ───────────────────────────────────────────────────────────
    elif any(k in question_lower for k in ["state", "district", "region", "concentration"]):
        result = await db.execute(
            select(
                Project.state,
                func.count(Project.id).label("count"),
                func.avg(Project.risk_score).label("avg_risk"),
                func.count(
                    func.nullif(Project.risk_level == "CRITICAL", False)
                ).label("critical_count"),
            )
            .group_by(Project.state)
            .order_by(func.avg(Project.risk_score).desc())
            .limit(5)
        )
        rows = result.all()
        records = [
            {
                "state": r.state,
                "project_count": r.count,
                "avg_risk_score": round(float(r.avg_risk or 0), 1),
            }
            for r in rows
        ]
        return {
            "answer": "States ranked by average project risk score (highest to lowest). Top 5 shown.",
            "records": records,
            "source": "Ledger Lens project database (SYNTHETIC DEMO)",
        }

    # ─── Default ──────────────────────────────────────────────────────────────
    else:
        return {
            "answer": (
                "I can help you explore the Ledger Lens data. "
                "Try asking: 'Show critical-risk projects', "
                "'Which projects have payment-progress mismatch?', "
                "'Show delayed projects', "
                "'Show financial outliers', or "
                "'Which states have the highest risk concentration?'"
            ),
            "records": [],
            "source": None,
        }
