"""Pydantic v2 validation models for MPLADS dataset ingestion and quality assurance.
"""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class MPAllocationRawRecord(BaseModel):
    """Raw record schema as loaded directly from the official CSV export."""
    sr_no: str = Field(..., alias="Sr. No.", description="Raw serial number or Grand Total tag")
    state: str = Field(..., alias="State", description="State or Union Territory")
    mp_name: str = Field(..., alias="Hon'ble Members of Parliaments", description="Member of Parliament name")
    constituency: str = Field(..., alias="Constituency", description="Lok Sabha Constituency")
    allocated_amount_raw: str = Field(..., alias="Allocated AMOUNT ( ₹ )", description="Raw currency string")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class MPAllocationCleanedRecord(BaseModel):
    """Cleaned and validated MP Allocation record for downstream analytics and PostgreSQL layer."""
    sr_no: int = Field(..., description="1-indexed sequence identifier")
    state: str = Field(..., description="Cleaned State or Union Territory name")
    mp_name: str = Field(..., description="Cleaned Member of Parliament name")
    constituency: str = Field(..., description="Standardized Constituency name")
    constituency_clean: str = Field(..., description="Constituency name stripped of reservation codes")
    allocated_amount_inr: float = Field(..., ge=0.0, description="Cleaned allocation limit in INR")
    
    # Domain & reservation metadata
    is_reserved_sc: bool = Field(default=False, description="Whether constituency is SC reserved")
    is_reserved_st: bool = Field(default=False, description="Whether constituency is ST reserved")
    
    # Data Quality & Integrity Flags
    is_missing_amount: bool = Field(default=False, description="True if amount was missing or null in raw source")
    is_invalid_amount: bool = Field(default=False, description="True if amount failed numerical parsing or was negative")
    is_duplicate_constituency: bool = Field(default=False, description="True if constituency appears more than once in dataset")
    is_data_quality_issue: bool = Field(default=False, description="True if any data anomaly or quality flag is raised")

    @field_validator("allocated_amount_inr")
    @classmethod
    def validate_amount_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Allocation amount cannot be negative")
        return v


class SummaryTotalsMetadata(BaseModel):
    """Metadata representing the official Grand Total summary row for audit reconciliation."""
    source_filename: str
    official_grand_total_inr: float
    calculated_sum_inr: float
    total_mp_records: int
    is_sum_reconciled: bool
    reconciliation_delta: float
