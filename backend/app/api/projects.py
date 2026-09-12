"""Projects and MP Allocations API endpoints."""

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MPAllocation, Project, RiskScore
from ..schemas import (
    MPAllocationSchema, MPAllocationListItem, ProjectListItem, ProjectDetail,
    RiskScoreSchema, ProjectRiskDetail, PaginationMeta
)
from ..ml.risk_engine import ProjectRiskEngine, MPRiskEngine
from ..ml.features import engineer_project_features
import pandas as pd

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", summary="List projects with filtering and pagination")
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in description, MP name, district"),
    state: Optional[str] = Query(None, description="Filter by state"),
    district: Optional[str] = Query(None, description="Filter by district"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW|MODERATE|HIGH|CRITICAL"),
    status: Optional[str] = Query(None, description="Filter by project status"),
    work_category: Optional[str] = Query(None, description="Filter by work category"),
    sort_by: str = Query("risk_score", description="Sort field: risk_score|sanctioned_amount|delay_days|project_age_days"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: AsyncSession = Depends(get_db),
):
    """List project records with server-side pagination, search, and filtering."""
    query = select(Project)

    # Filters
    filters = []
    if search:
        filters.append(or_(
            Project.work_description.ilike(f"%{search}%"),
            Project.mp_name.ilike(f"%{search}%"),
            Project.district.ilike(f"%{search}%"),
            Project.project_id.ilike(f"%{search}%"),
        ))
    if state:
        filters.append(Project.state == state)
    if district:
        filters.append(Project.district.ilike(f"%{district}%"))
    if risk_level:
        filters.append(Project.risk_level == risk_level)
    if status:
        filters.append(Project.status == status)
    if work_category:
        filters.append(Project.work_category == work_category)

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    sort_col = getattr(Project, sort_by, Project.risk_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    rows = (await db.execute(query)).scalars().all()

    return {
        "data": [ProjectListItem.model_validate(r) for r in rows],
        "pagination": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if per_page > 0 else 1,
        ),
    }


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get full project detail."""
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return ProjectDetail.model_validate(project)


@router.get("/{project_id}/risk", response_model=ProjectRiskDetail)
async def get_project_risk(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed risk analysis for a project."""
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    # Get stored risk score
    rs_result = await db.execute(
        select(RiskScore).where(
            RiskScore.entity_type == "project",
            RiskScore.entity_id == project_id,
        ).order_by(RiskScore.computed_at.desc()).limit(1)
    )
    risk_score_row = rs_result.scalar_one_or_none()

    # If no stored score, compute on the fly
    if not risk_score_row:
        engine = ProjectRiskEngine()
        record = {c.name: getattr(project, c.name) for c in Project.__table__.columns}
        risk_result = engine.score(record)

        risk_score_schema = RiskScoreSchema(
            entity_id=project_id,
            entity_type="project",
            overall_score=risk_result.overall_score,
            risk_level=risk_result.risk_level,
            financial_risk=risk_result.financial_risk,
            progress_risk=risk_result.progress_risk,
            timeline_risk=risk_result.timeline_risk,
            rule_risk=risk_result.rule_risk,
            similarity_risk=risk_result.similarity_risk,
            data_quality_risk=risk_result.data_quality_risk,
            weights_used=risk_result.weights_used,
            top_signals=risk_result.top_signals,
            triggered_rules=risk_result.triggered_rules,
            computed_at=None,
        )
        explanation = risk_result.explanation
        recommended = risk_result.recommended_verification
    else:
        risk_score_schema = RiskScoreSchema.model_validate(risk_score_row)
        engine = ProjectRiskEngine()
        record = {c.name: getattr(project, c.name) for c in Project.__table__.columns}
        risk_result = engine.score(record)
        explanation = risk_result.explanation
        recommended = risk_result.recommended_verification

    return ProjectRiskDetail(
        project=ProjectDetail.model_validate(project),
        risk_score=risk_score_schema,
        explanation=explanation,
        recommended_verification=recommended,
    )


@router.get("/{project_id}/similar")
async def get_similar_projects(
    project_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Find potentially similar projects by category, state, and amount range."""
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    # Simple similarity: same category + state, similar amount
    amount = project.sanctioned_amount
    lower = amount * 0.5
    upper = amount * 2.0

    similar_query = (
        select(Project)
        .where(
            Project.project_id != project_id,
            Project.work_category == project.work_category,
            Project.state == project.state,
            Project.sanctioned_amount.between(lower, upper),
        )
        .order_by(Project.sanctioned_amount.asc())
        .limit(limit)
    )

    similar = (await db.execute(similar_query)).scalars().all()

    results = []
    for sim in similar:
        # Simple similarity score based on category + state match
        score = 0.7  # base for same category + state
        if sim.district == project.district:
            score += 0.15
        if sim.implementing_agency == project.implementing_agency:
            score += 0.10
        if sim.mp_name == project.mp_name:
            score += 0.05

        results.append({
            "project_id": sim.project_id,
            "work_description": sim.work_description[:100] + "...",
            "work_category": sim.work_category,
            "state": sim.state,
            "district": sim.district,
            "sanctioned_amount": sim.sanctioned_amount,
            "similarity_score": round(min(score, 0.99), 2),
            "matching_attributes": [
                "Work Category", "State",
                *(["District"] if sim.district == project.district else []),
                *(["Implementing Agency"] if sim.implementing_agency == project.implementing_agency else []),
            ],
            "is_demo_record": sim.is_demo_record,
        })

    return {
        "source_project": {
            "project_id": project.project_id,
            "work_description": project.work_description[:100],
            "work_category": project.work_category,
            "state": project.state,
            "sanctioned_amount": project.sanctioned_amount,
        },
        "similar_projects": sorted(results, key=lambda x: -x["similarity_score"]),
        "note": "Potentially Similar Works — similarity is based on category, state, and amount. This does NOT imply duplication.",
    }


# ─── MP Allocations ──────────────────────────────────────────────────────────

mp_router = APIRouter(prefix="/mp-allocations", tags=["MP Allocations"])


@mp_router.get("", summary="List MP allocation records")
async def list_mp_allocations(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    outlier_only: bool = Query(False),
    sort_by: str = Query("anomaly_score"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """List MP allocation records."""
    query = select(MPAllocation)
    filters = []

    if search:
        filters.append(or_(
            MPAllocation.mp_name.ilike(f"%{search}%"),
            MPAllocation.constituency_clean.ilike(f"%{search}%"),
        ))
    if state:
        filters.append(MPAllocation.state == state)
    if outlier_only:
        filters.append(MPAllocation.is_financial_outlier == True)

    if filters:
        query = query.where(and_(*filters))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

    sort_col = getattr(MPAllocation, sort_by, MPAllocation.anomaly_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    return {
        "data": [MPAllocationListItem.model_validate(r) for r in rows],
        "pagination": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if per_page > 0 else 1,
        ),
    }


@mp_router.get("/{mp_id}", response_model=MPAllocationSchema)
async def get_mp_allocation(mp_id: int, db: AsyncSession = Depends(get_db)):
    """Get MP allocation detail."""
    result = await db.execute(select(MPAllocation).where(MPAllocation.id == mp_id))
    mp = result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="MP allocation record not found.")
    return MPAllocationSchema.model_validate(mp)
