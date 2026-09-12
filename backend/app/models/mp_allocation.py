"""SQLAlchemy model for real MP Allocation data from official eSAKSHI/MPLADS source."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class MPAllocation(Base):
    """Represents a single MP's MPLADS fund allocation record.

    Source: Official eSAKSHI portal export.
    Data is REAL and IMMUTABLE from source.
    """

    __tablename__ = "mp_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sr_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mp_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    constituency: Mapped[str] = mapped_column(String(200), nullable=False)
    constituency_clean: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    allocated_amount_inr: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Reservation metadata
    is_reserved_sc: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reserved_st: Mapped[bool] = mapped_column(Boolean, default=False)

    # Data quality flags
    is_missing_amount: Mapped[bool] = mapped_column(Boolean, default=False)
    is_invalid_amount: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate_constituency: Mapped[bool] = mapped_column(Boolean, default=False)
    is_data_quality_issue: Mapped[bool] = mapped_column(Boolean, default=False)

    # Computed financial features (populated after ML run)
    allocation_zscore: Mapped[float] = mapped_column(Float, nullable=True)
    state_peer_deviation_pct: Mapped[float] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=True)
    is_financial_outlier: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<MPAllocation sr={self.sr_no} mp={self.mp_name} state={self.state}>"
