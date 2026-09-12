"""Pydantic response schemas for Ledger Lens API."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Pagination ────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel):
    data: List[Any]
    pagination: PaginationMeta


# ─── MP Allocation ─────────────────────────────────────────────────────────────

class MPAllocationSchema(BaseModel):
    id: int
    sr_no: int
    state: str
    mp_name: str
    constituency: str
    constituency_clean: str
    allocated_amount_inr: float
    is_reserved_sc: bool
    is_reserved_st: bool
    is_missing_amount: bool
    is_invalid_amount: bool
    is_duplicate_constituency: bool
    is_data_quality_issue: bool
    allocation_zscore: Optional[float]
    state_peer_deviation_pct: Optional[float]
    anomaly_score: Optional[float]
    is_financial_outlier: bool

    model_config = {"from_attributes": True}


class MPAllocationListItem(BaseModel):
    id: int
    sr_no: int
    state: str
    mp_name: str
    constituency_clean: str
    allocated_amount_inr: float
    anomaly_score: Optional[float]
    is_financial_outlier: bool
    is_data_quality_issue: bool
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None

    model_config = {"from_attributes": True}


# ─── Projects ─────────────────────────────────────────────────────────────────

class ProjectListItem(BaseModel):
    id: int
    project_id: str
    work_description: str
    work_category: Optional[str]
    state: str
    district: Optional[str]
    constituency: Optional[str]
    mp_name: Optional[str]
    sanctioned_amount: float
    expenditure_amount: Optional[float]
    utilization_ratio: Optional[float]
    physical_progress_pct: Optional[float]
    status: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    delay_days: Optional[int]
    is_demo_record: bool
    data_source: str

    model_config = {"from_attributes": True}


class ProjectDetail(BaseModel):
    id: int
    project_id: str
    work_description: str
    work_category: Optional[str]
    sector: Optional[str]
    state: str
    district: Optional[str]
    constituency: Optional[str]
    location_detail: Optional[str]
    mp_name: Optional[str]
    sanctioned_amount: float
    expenditure_amount: Optional[float]
    utilization_ratio: Optional[float]
    implementing_agency: Optional[str]
    sanction_date: Optional[date]
    start_date: Optional[date]
    expected_completion_date: Optional[date]
    actual_completion_date: Optional[date]
    project_age_days: Optional[int]
    delay_days: Optional[int]
    physical_progress_pct: Optional[float]
    financial_progress_pct: Optional[float]
    payment_progress_gap: Optional[float]
    status: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    is_demo_record: bool
    data_source: str

    model_config = {"from_attributes": True}


# ─── Risk Scores ──────────────────────────────────────────────────────────────

class RiskSignalSchema(BaseModel):
    type: str
    name: str
    severity: str
    description: str
    evidence: Optional[Dict[str, Any]]


class RiskScoreSchema(BaseModel):
    entity_id: str
    entity_type: str
    overall_score: float
    risk_level: str
    financial_risk: Optional[float]
    progress_risk: Optional[float]
    timeline_risk: Optional[float]
    rule_risk: Optional[float]
    similarity_risk: Optional[float]
    data_quality_risk: Optional[float]
    weights_used: Optional[Dict[str, float]]
    top_signals: Optional[List[Dict[str, Any]]]
    triggered_rules: Optional[List[str]]
    computed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProjectRiskDetail(BaseModel):
    project: ProjectDetail
    risk_score: RiskScoreSchema
    explanation: str
    recommended_verification: List[str]


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_mp_records: int
    total_projects: int
    total_sanctioned_amount: float
    total_expenditure: float
    high_risk_count: int
    critical_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    projects_requiring_verification: int
    delayed_projects: int
    financial_outliers: int
    data_quality_issues: int
    demo_mode: bool
    data_source_label: str
    last_updated: datetime


class RiskDistribution(BaseModel):
    risk_level: str
    count: int
    percentage: float
    color: str


class StateRiskSummary(BaseModel):
    state: str
    total_records: int
    avg_risk_score: float
    critical_count: int
    high_count: int
    total_allocation: float


# ─── Verification ─────────────────────────────────────────────────────────────

class VerificationCaseSchema(BaseModel):
    id: int
    case_id: str
    entity_type: str
    entity_id: str
    status: str
    assigned_to: Optional[str]
    priority: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    primary_signal: Optional[str]
    resolution_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VerificationUpdateRequest(BaseModel):
    status: str
    assigned_to: Optional[str] = None
    resolution_summary: Optional[str] = None
    officer_name: str = "Monitoring Officer"
    note_text: Optional[str] = None


# ─── Analytics ────────────────────────────────────────────────────────────────

class StateAnalytics(BaseModel):
    state: str
    mp_count: int
    total_allocation: float
    avg_allocation: float
    financial_outlier_count: int
    data_quality_issues: int
    avg_anomaly_score: Optional[float]


class ProjectAnalytics(BaseModel):
    total_projects: int
    by_status: Dict[str, int]
    by_risk_level: Dict[str, int]
    by_sector: Dict[str, int]
    avg_utilization: float
    avg_delay_days: float
    payment_mismatch_count: int


# ─── Data Quality ─────────────────────────────────────────────────────────────

class DataQualitySummary(BaseModel):
    total_mp_records: int
    missing_amounts: int
    invalid_amounts: int
    duplicate_constituencies: int
    financial_outliers: int
    data_quality_score: float
    data_quality_label: str
    methodology_note: str


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    demo_mode: bool
    database: str
    mp_records_loaded: int
    projects_loaded: int
    timestamp: datetime
