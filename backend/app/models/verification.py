"""SQLAlchemy models for human-in-the-loop verification workflow."""

import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class VerificationStatus(str, enum.Enum):
    AI_FLAGGED = "AI_FLAGGED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    FALSE_SIGNAL = "FALSE_SIGNAL"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    RESOLVED = "RESOLVED"


class VerificationCase(Base):
    """Human verification case for a flagged project or MP allocation.

    AI never marks 'fraud confirmed'. Officers make the final decision.
    """

    __tablename__ = "verification_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Reference
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'project' | 'mp'
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Status
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus),
        default=VerificationStatus.AI_FLAGGED,
        nullable=False,
        index=True,
    )

    # Assignment
    assigned_to: Mapped[str] = mapped_column(String(200), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")  # LOW/NORMAL/HIGH/URGENT

    # Summary
    risk_score: Mapped[float] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=True)
    primary_signal: Mapped[str] = mapped_column(String(200), nullable=True)

    # Resolution
    resolution_summary: Mapped[str] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<VerificationCase {self.case_id} status={self.status}>"


class VerificationNote(Base):
    """Officer notes on a verification case."""

    __tablename__ = "verification_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    officer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AuditLog(Base):
    """Full audit trail for all verification actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
