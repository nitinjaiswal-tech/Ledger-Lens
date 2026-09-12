"""Alerts API — risk flags requiring human attention."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Project, RiskScore, VerificationCase
from ..schemas import PaginationMeta

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("")
async def list_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None),
    risk_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List risk alerts from high and critical risk projects."""
    query = select(Project).where(
        Project.risk_level.in_(["HIGH", "CRITICAL", "MODERATE"])
    )

    if risk_level:
        query = query.where(Project.risk_level == risk_level)
    if state:
        query = query.where(Project.state == state)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(Project.risk_score.desc().nulls_last())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    alerts = []
    for proj in rows:
        # Get risk signals from stored risk score
        rs_result = await db.execute(
            select(RiskScore).where(
                RiskScore.entity_type == "project",
                RiskScore.entity_id == proj.project_id,
            ).order_by(RiskScore.computed_at.desc()).limit(1)
        )
        rs = rs_result.scalar_one_or_none()
        top_signals = (rs.top_signals or []) if rs else []
        primary_signal = top_signals[0]["name"] if top_signals else "Risk Signal"

        alerts.append({
            "alert_id": f"ALERT-{proj.project_id}",
            "project_id": proj.project_id,
            "work_description": proj.work_description[:80] + "...",
            "state": proj.state,
            "district": proj.district,
            "risk_level": proj.risk_level.value if hasattr(proj.risk_level, 'value') else proj.risk_level,
            "risk_score": proj.risk_score,
            "primary_signal": primary_signal,
            "top_signals": top_signals[:3],
            "sanctioned_amount": proj.sanctioned_amount,
            "utilization_ratio": proj.utilization_ratio,
            "physical_progress_pct": proj.physical_progress_pct,
            "delay_days": proj.delay_days,
            "mp_name": proj.mp_name,
            "is_demo_record": proj.is_demo_record,
            "detected_at": proj.created_at.isoformat() if proj.created_at else None,
        })

    return {
        "data": alerts,
        "pagination": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if per_page > 0 else 1,
        ),
    }
