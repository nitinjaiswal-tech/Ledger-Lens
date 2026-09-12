"""Verification workflow API — human-in-the-loop case management."""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import VerificationCase, VerificationNote, AuditLog, VerificationStatus
from ..schemas import VerificationCaseSchema, VerificationUpdateRequest, PaginationMeta

router = APIRouter(prefix="/verification", tags=["Verification"])

VALID_STATUSES = {s.value for s in VerificationStatus}


@router.get("", summary="List verification cases")
async def list_verification_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List verification cases."""
    query = select(VerificationCase)

    if status:
        query = query.where(VerificationCase.status == status)
    if priority:
        query = query.where(VerificationCase.priority == priority)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(VerificationCase.updated_at.desc())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    return {
        "data": [VerificationCaseSchema.model_validate(r) for r in rows],
        "pagination": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if per_page > 0 else 1,
        ),
    }


@router.get("/{case_id}", response_model=VerificationCaseSchema)
async def get_verification_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Get a verification case by ID."""
    result = await db.execute(
        select(VerificationCase).where(VerificationCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return VerificationCaseSchema.model_validate(case)


@router.patch("/{case_id}", response_model=VerificationCaseSchema)
async def update_verification_case(
    case_id: str,
    update: VerificationUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update verification case status.

    Valid status transitions:
        AI_FLAGGED → UNDER_REVIEW → VERIFIED | FALSE_SIGNAL | ACTION_REQUIRED → RESOLVED

    NOTE: This system NEVER allows status 'FRAUD_CONFIRMED'.
    Officers make the final decision.
    """
    if update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{update.status}'. Valid: {sorted(VALID_STATUSES)}",
        )

    result = await db.execute(
        select(VerificationCase).where(VerificationCase.case_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    old_status = case.status.value if hasattr(case.status, 'value') else str(case.status)

    # Update case
    case.status = VerificationStatus(update.status)
    if update.assigned_to:
        case.assigned_to = update.assigned_to
    if update.resolution_summary:
        case.resolution_summary = update.resolution_summary
    if update.status in ("VERIFIED", "FALSE_SIGNAL", "ACTION_REQUIRED", "RESOLVED"):
        case.resolved_at = datetime.utcnow()

    # Add note
    if update.note_text:
        note = VerificationNote(
            case_id=case_id,
            officer_name=update.officer_name,
            note_text=update.note_text,
            action_taken=update.status,
        )
        db.add(note)

    # Audit log
    audit = AuditLog(
        event_type="VERIFICATION_STATUS_CHANGE",
        entity_type="verification_case",
        entity_id=case_id,
        actor=update.officer_name,
        description=f"Status changed from {old_status} to {update.status}",
        old_value=old_status,
        new_value=update.status,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(case)
    return VerificationCaseSchema.model_validate(case)


@router.get("/{case_id}/notes")
async def get_case_notes(case_id: str, db: AsyncSession = Depends(get_db)):
    """Get all notes for a verification case."""
    result = await db.execute(
        select(VerificationNote)
        .where(VerificationNote.case_id == case_id)
        .order_by(VerificationNote.created_at.asc())
    )
    notes = result.scalars().all()
    return [
        {
            "id": n.id,
            "officer_name": n.officer_name,
            "note_text": n.note_text,
            "action_taken": n.action_taken,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]
