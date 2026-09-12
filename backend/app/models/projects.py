"""SQLAlchemy model for MPLADS project/work records.

IMPORTANT: When is_demo_record=True, this record is SYNTHETIC and clearly labeled.
Real project-level data is not available in the current dataset.
"""

import enum
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ProjectStatus(str, enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    STALLED = "Stalled"
    UNDER_REVIEW = "Under Review"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Project(Base):
    """Represents an MPLADS project/work record.

    When is_demo_record=True: Synthetic demonstration record, NOT official government data.
    When is_demo_record=False: Real project data (when available from eSAKSHI).
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    project_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    work_description: Mapped[str] = mapped_column(Text, nullable=False)
    work_category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    # Geographic
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    constituency: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    location_detail: Mapped[str] = mapped_column(String(300), nullable=True)

    # MP linkage (references real MP data)
    mp_name: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    mp_allocation_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Financial
    sanctioned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    expenditure_amount: Mapped[float] = mapped_column(Float, nullable=True)
    utilization_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    implementing_agency: Mapped[str] = mapped_column(String(200), nullable=True, index=True)

    # Timeline
    sanction_date: Mapped[date] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    expected_completion_date: Mapped[date] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[date] = mapped_column(Date, nullable=True)
    project_age_days: Mapped[int] = mapped_column(Integer, nullable=True)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=True)

    # Progress
    physical_progress_pct: Mapped[float] = mapped_column(Float, nullable=True)
    financial_progress_pct: Mapped[float] = mapped_column(Float, nullable=True)
    payment_progress_gap: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.IN_PROGRESS, index=True
    )

    # Risk (computed)
    risk_score: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel), nullable=True, index=True
    )

    # Data Provenance — CRITICAL
    is_demo_record: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    data_source: Mapped[str] = mapped_column(
        String(100), default="SYNTHETIC_DEMO", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Project {self.project_id} [{self.risk_level}]>"
