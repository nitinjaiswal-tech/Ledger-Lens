"""SQLAlchemy models for risk scores and risk signals."""

from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RiskScore(Base):
    """Computed multi-signal risk score for a project or MP allocation."""

    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Reference (either project_id or mp_allocation_id)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'project' | 'mp'
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Composite score
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Component scores (0–100 each)
    financial_risk: Mapped[float] = mapped_column(Float, nullable=True)
    progress_risk: Mapped[float] = mapped_column(Float, nullable=True)
    timeline_risk: Mapped[float] = mapped_column(Float, nullable=True)
    similarity_risk: Mapped[float] = mapped_column(Float, nullable=True)
    rule_risk: Mapped[float] = mapped_column(Float, nullable=True)
    data_quality_risk: Mapped[float] = mapped_column(Float, nullable=True)

    # Weights used (stored for auditability)
    weights_used: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Top signals (stored as JSON list)
    top_signals: Mapped[list] = mapped_column(JSON, nullable=True)

    # Triggered rules (list of rule IDs)
    triggered_rules: Mapped[list] = mapped_column(JSON, nullable=True)

    # Model versioning
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    feature_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RiskScore entity={self.entity_id} score={self.overall_score} level={self.risk_level}>"


class RiskSignal(Base):
    """Individual risk signal contributing to a risk score."""

    __tablename__ = "risk_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_score_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Signal identity
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low/medium/high/critical

    # Evidence
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=True)
    affected_fields: Mapped[list] = mapped_column(JSON, nullable=True)

    # Contribution
    contribution_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
