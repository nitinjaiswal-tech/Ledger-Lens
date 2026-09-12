"""
Ledger Lens — Feature Engineering Layer

Creates meaningful, analysis-ready features from available MPLADS data.

Data available:
- MP allocation data (REAL): sr_no, state, mp_name, constituency, allocated_amount_inr
- Project data (DEMO): financial, timeline, progress fields

Features generated:
1. Financial features: z-score, IQR flags, peer deviations (from REAL data)
2. Project features: utilization_ratio, delay_days, payment_progress_gap (from DEMO)

All feature engineering is documented and reproducible.
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats


MODEL_VERSION = "1.0.0"
FEATURE_VERSION = "1.0.0"


def engineer_mp_financial_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer financial features from the real MP allocation dataset.

    Input columns expected: state, allocated_amount_inr

    Output adds:
        allocation_zscore          — Z-score vs national distribution
        allocation_iqr_flag_high   — True if above Q3 + 1.5*IQR
        allocation_iqr_flag_low    — True if below Q1 - 1.5*IQR
        state_mean_amount          — State-level average allocation
        state_peer_deviation_pct   — % deviation from state peer mean
        national_mean_amount       — National average
        national_median_amount     — National median
        allocation_percentile      — Percentile rank (0-100)
        is_financial_outlier       — True if z-score > 2.5 or IQR flagged
    """
    df = df.copy()

    # Drop previously computed feature columns if present to avoid duplicate columns on merge
    drop_cols = [c for c in [
        "national_mean_amount", "national_median_amount", "allocation_zscore",
        "allocation_iqr_flag_high", "allocation_iqr_flag_low", "allocation_percentile",
        "state_mean", "state_median", "state_peer_deviation_pct", "is_financial_outlier"
    ] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    amounts = df["allocated_amount_inr"].values

    # National statistics (exclude zero amounts for anomaly detection)
    nonzero = amounts[amounts > 0]
    national_mean = float(np.mean(nonzero))
    national_std = float(np.std(nonzero, ddof=1))
    national_median = float(np.median(nonzero))
    q1 = float(np.percentile(nonzero, 25))
    q3 = float(np.percentile(nonzero, 75))
    iqr = q3 - q1

    df["national_mean_amount"] = national_mean
    df["national_median_amount"] = national_median

    # Z-score (for records with nonzero amounts)
    df["allocation_zscore"] = np.where(
        df["allocated_amount_inr"] > 0,
        (df["allocated_amount_inr"] - national_mean) / (national_std + 1e-10),
        0.0,
    )

    # IQR outlier flags
    df["allocation_iqr_flag_high"] = df["allocated_amount_inr"] > (q3 + 1.5 * iqr)
    df["allocation_iqr_flag_low"] = (
        (df["allocated_amount_inr"] < (q1 - 1.5 * iqr)) & (df["allocated_amount_inr"] > 0)
    )

    # Percentile rank
    df["allocation_percentile"] = df["allocated_amount_inr"].rank(pct=True) * 100

    # State-level peer comparison
    state_stats = (
        df[df["allocated_amount_inr"] > 0]
        .groupby("state")["allocated_amount_inr"]
        .agg(state_mean="mean", state_median="median")
        .reset_index()
    )
    df = df.merge(state_stats, on="state", how="left")

    # % deviation from state peer mean
    df["state_peer_deviation_pct"] = np.where(
        (df["allocated_amount_inr"] > 0) & (df["state_mean"] > 0),
        ((df["allocated_amount_inr"] - df["state_mean"]) / df["state_mean"]) * 100,
        0.0,
    )

    # Composite outlier flag
    df["is_financial_outlier"] = (
        (df["allocation_zscore"].abs() > 2.5)
        | df["allocation_iqr_flag_high"]
        | df["allocation_iqr_flag_low"]
    )

    return df


def engineer_project_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer project-level features for risk analysis.

    Expected input columns (from demo/real projects):
        sanctioned_amount, expenditure_amount, utilization_ratio,
        physical_progress_pct, financial_progress_pct, project_age_days,
        delay_days, work_category, state, district

    Output adds:
        amount_zscore_vs_peers       — Z-score vs same-category projects
        category_peer_deviation_pct  — Deviation from category mean
        progress_velocity            — Progress per 100 days
        progress_stagnation          — True if age > 365 days but progress < 30%
        payment_progress_gap         — financial_pct - physical_pct
        gap_severity                 — "critical" / "high" / "moderate" / "normal"
        delay_category               — "No Delay" / "Watch" / "Delayed" / "Severely Delayed"
        is_stalled                   — True if progress < 5% and age > 180
        utilization_risk             — 0-100 score
        peer_amount_deviation_pct    — vs state+category peers
    """
    df = df.copy()

    # Payment-progress gap severity
    if "payment_progress_gap" not in df.columns and all(
        c in df.columns for c in ["financial_progress_pct", "physical_progress_pct"]
    ):
        df["payment_progress_gap"] = df["financial_progress_pct"] - df["physical_progress_pct"]

    if "payment_progress_gap" in df.columns:
        gap = df["payment_progress_gap"]
        conditions = [gap > 40, gap > 20, gap > 10, gap <= 10]
        choices = ["critical", "high", "moderate", "normal"]
        df["gap_severity"] = np.select(conditions, choices, default="normal")
    else:
        df["payment_progress_gap"] = 0.0
        df["gap_severity"] = "normal"

    # Delay classification (configurable thresholds in days)
    if "delay_days" in df.columns:
        delay = df["delay_days"]
        conditions = [delay <= 0, delay <= 90, delay <= 365, delay > 365]
        choices = ["No Delay", "Watch", "Delayed", "Severely Delayed"]
        df["delay_category"] = np.select(conditions, choices, default="No Delay")
    else:
        df["delay_category"] = "No Delay"

    # Progress velocity (% progress per 100 days)
    if all(c in df.columns for c in ["physical_progress_pct", "project_age_days"]):
        df["progress_velocity"] = np.where(
            df["project_age_days"] > 0,
            (df["physical_progress_pct"] / df["project_age_days"]) * 100,
            0.0,
        )
        # Stagnation: project is old but progress is very low
        df["progress_stagnation"] = (
            (df["project_age_days"] > 365) & (df["physical_progress_pct"] < 30.0)
        )
        df["is_stalled"] = (
            (df["project_age_days"] > 180) & (df["physical_progress_pct"] < 5.0)
        )
    else:
        df["progress_velocity"] = 0.0
        df["progress_stagnation"] = False
        df["is_stalled"] = False

    # Category peer comparison for amounts
    if "work_category" in df.columns and "sanctioned_amount" in df.columns:
        cat_stats = (
            df.groupby("work_category")["sanctioned_amount"]
            .agg(cat_mean="mean", cat_median="median", cat_std="std")
            .reset_index()
        )
        df = df.merge(cat_stats, on="work_category", how="left")
        df["amount_zscore_vs_peers"] = np.where(
            df["cat_std"] > 0,
            (df["sanctioned_amount"] - df["cat_mean"]) / df["cat_std"],
            0.0,
        )
        df["category_peer_deviation_pct"] = np.where(
            df["cat_mean"] > 0,
            ((df["sanctioned_amount"] - df["cat_mean"]) / df["cat_mean"]) * 100,
            0.0,
        )
    else:
        df["amount_zscore_vs_peers"] = 0.0
        df["category_peer_deviation_pct"] = 0.0

    # Utilization risk score (0–100): high if overutilized or very low despite age
    if "utilization_ratio" in df.columns:
        u = df["utilization_ratio"]
        # Penalize overutilization (>1.0) and underutilization with age
        df["utilization_risk"] = np.clip(
            np.where(u > 1.0, (u - 1.0) * 200, np.where(u < 0.3, (0.3 - u) * 100, 0)),
            0, 100,
        )
    else:
        df["utilization_risk"] = 0.0

    return df


def build_isolation_forest_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """
    Build the feature matrix for Isolation Forest from engineered features.

    Returns:
        (X, feature_names) — numpy array and list of feature name strings
    """
    feature_cols = []

    candidate_cols = [
        "allocation_zscore",
        "state_peer_deviation_pct",
        "allocation_percentile",
        "is_financial_outlier",
        "is_missing_amount",
        "is_duplicate_constituency",
    ]

    available = [c for c in candidate_cols if c in df.columns]
    feature_cols = available

    X = df[feature_cols].fillna(0).astype(float).values
    return X, feature_cols


def build_project_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """Build feature matrix for project-level anomaly detection."""
    candidate_cols = [
        "utilization_ratio",
        "physical_progress_pct",
        "payment_progress_gap",
        "delay_days",
        "project_age_days",
        "amount_zscore_vs_peers",
        "progress_velocity",
    ]
    available = [c for c in candidate_cols if c in df.columns]
    X = df[available].fillna(0).astype(float).values
    return X, available
