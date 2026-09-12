"""
Ledger Lens — Data Ingestion Service

Loads real MP allocation data and demo project data into the SQLite database.
Runs ML pipeline (feature engineering + anomaly detection + risk scoring) on ingest.

Data flow:
    Real MP data (parquet) → feature engineering → anomaly detection → risk scoring → DB
    Demo projects (synthetic) → feature engineering → risk scoring → DB
    Risk scores → DB
    Verification cases (auto-created for HIGH/CRITICAL) → DB
"""

import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..data.cleaner import DataCleaner
from ..models import MPAllocation, Project, ProjectStatus, RiskLevel, RiskScore, RiskSignal, VerificationCase, VerificationStatus, AuditLog
from ..ml.features import engineer_mp_financial_features, engineer_project_features
from ..ml.financial_anomaly import run_mp_anomaly_detection
from ..ml.risk_engine import MPRiskEngine, ProjectRiskEngine
from ..ml.demo_data import generate_demo_projects

logger = logging.getLogger(__name__)
settings = get_settings()


async def is_db_populated(session: AsyncSession) -> bool:
    """Check if the database already has data."""
    result = await session.execute(select(func.count()).select_from(MPAllocation))
    count = result.scalar()
    return (count or 0) > 0


async def ingest_all(session: AsyncSession, force: bool = False) -> dict:
    """
    Main ingestion entry point. Loads all data into the database.

    Args:
        session: SQLAlchemy async session
        force: If True, re-ingest even if data exists

    Returns:
        Summary dict with counts and status.
    """
    if not force and await is_db_populated(session):
        logger.info("Database already populated. Skipping ingestion.")
        return {"status": "skipped", "reason": "already_populated"}

    logger.info("Starting data ingestion pipeline...")
    summary = {}

    try:
        # 1. Load and clean real MP data
        cleaner = DataCleaner()
        mp_df, meta = cleaner.process_mp_allocations()
        logger.info(f"Loaded {len(mp_df)} MP allocation records.")

        # 2. Feature engineering on real MP data
        mp_engineered = engineer_mp_financial_features(mp_df)
        logger.info("MP feature engineering complete.")

        # 3. Anomaly detection on real MP data
        mp_scored = run_mp_anomaly_detection(
            mp_engineered,
            contamination=settings.anomaly_contamination,
            models_path=settings.models_path,
        )
        logger.info("MP anomaly detection complete.")

        # 4. Insert MP allocations into DB
        mp_engine = MPRiskEngine()
        mp_records_inserted = 0

        for _, row in mp_scored.iterrows():
            record_dict = row.to_dict()
            # Clean NaN/inf
            for k, v in record_dict.items():
                if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                    record_dict[k] = None

            risk_result = mp_engine.score(record_dict)

            mp_obj = MPAllocation(
                sr_no=int(record_dict.get("sr_no", 0)),
                state=str(record_dict.get("state", "")),
                mp_name=str(record_dict.get("mp_name", "")),
                constituency=str(record_dict.get("constituency", "")),
                constituency_clean=str(record_dict.get("constituency_clean", "")),
                allocated_amount_inr=float(record_dict.get("allocated_amount_inr", 0.0)),
                is_reserved_sc=bool(record_dict.get("is_reserved_sc", False)),
                is_reserved_st=bool(record_dict.get("is_reserved_st", False)),
                is_missing_amount=bool(record_dict.get("is_missing_amount", False)),
                is_invalid_amount=bool(record_dict.get("is_invalid_amount", False)),
                is_duplicate_constituency=bool(record_dict.get("is_duplicate_constituency", False)),
                is_data_quality_issue=bool(record_dict.get("is_data_quality_issue", False)),
                allocation_zscore=_safe_float(record_dict.get("allocation_zscore")),
                state_peer_deviation_pct=_safe_float(record_dict.get("state_peer_deviation_pct")),
                anomaly_score=_safe_float(record_dict.get("anomaly_score")),
                is_financial_outlier=bool(record_dict.get("is_financial_outlier", False)),
            )
            session.add(mp_obj)
            mp_records_inserted += 1

            # Add risk score
            await session.flush()
            risk_score_obj = RiskScore(
                entity_type="mp",
                entity_id=str(record_dict.get("sr_no", "")),
                overall_score=risk_result.overall_score,
                risk_level=risk_result.risk_level,
                financial_risk=risk_result.financial_risk,
                data_quality_risk=risk_result.data_quality_risk,
                rule_risk=risk_result.rule_risk,
                weights_used=risk_result.weights_used,
                top_signals=risk_result.top_signals,
                triggered_rules=risk_result.triggered_rules,
            )
            session.add(risk_score_obj)

            # Auto-create verification case for HIGH/CRITICAL MP allocations
            if risk_result.risk_level in ("HIGH", "CRITICAL"):
                sig_name = (
                    risk_result.top_signals[0]["name"]
                    if risk_result.top_signals
                    else "Allocation Anomaly"
                )
                mp_case = VerificationCase(
                    case_id=f"CASE-MP-{int(record_dict.get('sr_no', 0)):04d}",
                    entity_type="mp",
                    entity_id=str(record_dict.get("sr_no", "")),
                    status=VerificationStatus.AI_FLAGGED,
                    priority="URGENT" if risk_result.risk_level == "CRITICAL" else "HIGH",
                    risk_score=risk_result.overall_score,
                    risk_level=risk_result.risk_level,
                    primary_signal=sig_name,
                )
                session.add(mp_case)

        await session.flush()
        summary["mp_records"] = mp_records_inserted
        logger.info(f"Inserted {mp_records_inserted} MP allocation records.")

        # 5. Generate and insert demo projects (if demo mode enabled)
        if settings.demo_mode:
            demo_projects = generate_demo_projects(mp_df, n_projects=settings.demo_projects_count)
            project_engine = ProjectRiskEngine()
            projects_inserted = 0

            # Engineer project features
            project_df = pd.DataFrame(demo_projects)
            project_df_engineered = engineer_project_features(project_df)

            for _, proj_row in project_df_engineered.iterrows():
                proj_dict = proj_row.to_dict()
                for k, v in proj_dict.items():
                    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                        proj_dict[k] = None

                # Parse dates safely
                sanction_date = _parse_date(proj_dict.get("sanction_date"))
                start_date = _parse_date(proj_dict.get("start_date"))
                expected_completion = _parse_date(proj_dict.get("expected_completion_date"))
                actual_completion = _parse_date(proj_dict.get("actual_completion_date"))

                status_str = proj_dict.get("status", "In Progress")
                try:
                    status_enum = ProjectStatus(status_str)
                except ValueError:
                    status_enum = ProjectStatus.IN_PROGRESS

                risk_result = project_engine.score(proj_dict)

                try:
                    risk_level_enum = RiskLevel(risk_result.risk_level)
                except ValueError:
                    risk_level_enum = RiskLevel.LOW

                proj_obj = Project(
                    project_id=proj_dict.get("project_id", f"DEMO-{projects_inserted}"),
                    work_description=str(proj_dict.get("work_description", ""))[:500],
                    work_category=str(proj_dict.get("work_category", ""))[:100],
                    sector=str(proj_dict.get("sector", ""))[:100],
                    state=str(proj_dict.get("state", ""))[:100],
                    district=str(proj_dict.get("district", ""))[:100],
                    constituency=str(proj_dict.get("constituency", ""))[:200],
                    location_detail=str(proj_dict.get("location_detail", ""))[:300],
                    mp_name=str(proj_dict.get("mp_name", ""))[:200],
                    mp_allocation_id=proj_dict.get("mp_allocation_id"),
                    sanctioned_amount=_safe_float(proj_dict.get("sanctioned_amount"), 0.0),
                    expenditure_amount=_safe_float(proj_dict.get("expenditure_amount"), 0.0),
                    utilization_ratio=_safe_float(proj_dict.get("utilization_ratio")),
                    implementing_agency=str(proj_dict.get("implementing_agency", ""))[:200],
                    sanction_date=sanction_date,
                    start_date=start_date,
                    expected_completion_date=expected_completion,
                    actual_completion_date=actual_completion,
                    project_age_days=_safe_int(proj_dict.get("project_age_days")),
                    delay_days=_safe_int(proj_dict.get("delay_days")),
                    physical_progress_pct=_safe_float(proj_dict.get("physical_progress_pct")),
                    financial_progress_pct=_safe_float(proj_dict.get("financial_progress_pct")),
                    payment_progress_gap=_safe_float(proj_dict.get("payment_progress_gap")),
                    status=status_enum,
                    risk_score=risk_result.overall_score,
                    risk_level=risk_level_enum,
                    is_demo_record=True,
                    data_source="SYNTHETIC_DEMO",
                )
                session.add(proj_obj)
                projects_inserted += 1

                # Risk score for project
                risk_score_obj = RiskScore(
                    entity_type="project",
                    entity_id=proj_dict.get("project_id", ""),
                    overall_score=risk_result.overall_score,
                    risk_level=risk_result.risk_level,
                    financial_risk=risk_result.financial_risk,
                    progress_risk=risk_result.progress_risk,
                    timeline_risk=risk_result.timeline_risk,
                    rule_risk=risk_result.rule_risk,
                    data_quality_risk=risk_result.data_quality_risk,
                    weights_used=risk_result.weights_used,
                    top_signals=risk_result.top_signals,
                    triggered_rules=risk_result.triggered_rules,
                )
                session.add(risk_score_obj)

                # Auto-create verification cases for HIGH/CRITICAL or severe mismatch
                gap = _safe_float(proj_dict.get("payment_progress_gap"), 0.0) or 0.0
                delay = _safe_int(proj_dict.get("delay_days"), 0) or 0
                if risk_result.risk_level in ("HIGH", "CRITICAL") or gap > 35 or delay > 300:
                    primary_signal = (
                        risk_result.top_signals[0]["name"]
                        if risk_result.top_signals
                        else "High Risk Discrepancy"
                    )
                    effective_level = risk_result.risk_level if risk_result.risk_level in ("HIGH", "CRITICAL") else "HIGH"
                    case = VerificationCase(
                        case_id=f"CASE-{uuid.uuid4().hex[:8].upper()}",
                        entity_type="project",
                        entity_id=proj_dict.get("project_id", ""),
                        status=VerificationStatus.AI_FLAGGED,
                        priority="URGENT" if (risk_result.risk_level == "CRITICAL" or delay > 500 or gap > 50) else "HIGH",
                        risk_score=risk_result.overall_score,
                        risk_level=effective_level,
                        primary_signal=primary_signal,
                    )
                    session.add(case)

            await session.commit()
            summary["demo_projects"] = projects_inserted
            logger.info(f"Inserted {projects_inserted} demo project records.")

        else:
            await session.commit()

        # Audit log
        audit = AuditLog(
            event_type="DATA_INGESTION_COMPLETE",
            entity_type="system",
            entity_id="ingestion",
            actor="SYSTEM",
            description=f"Ingestion complete. MP records: {summary.get('mp_records', 0)}, Demo projects: {summary.get('demo_projects', 0)}",
        )
        session.add(audit)
        await session.commit()

        summary["status"] = "success"
        logger.info(f"Ingestion complete: {summary}")
        return summary

    except Exception as e:
        await session.rollback()
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise


def _safe_float(val, default=None):
    """Convert value to float, returning default on failure."""
    try:
        if val is None:
            return default
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    """Convert value to int safely."""
    try:
        if val is None:
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _parse_date(val) -> Optional[date]:
    """Parse date string or date object."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None
