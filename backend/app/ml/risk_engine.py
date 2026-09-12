"""
Ledger Lens — Multi-Signal Risk Engine

Aggregates outputs from:
    1. Financial Anomaly (Isolation Forest) — 30%
    2. Progress Analysis                   — 20%
    3. Timeline / Delay Analysis           — 20%
    4. Rule Engine                         — 15%
    5. Similarity Detection                — 10%
    6. Data Quality                        —  5%

IMPORTANT DISCLAIMER:
These weights are DEFAULT DEMONSTRATION weights chosen for system illustration.
They do NOT represent an official government risk scoring methodology.
Weights are fully configurable via the settings system.

Risk Tiers:
    0–29   LOW
    30–59  MODERATE
    60–79  HIGH
    80–100 CRITICAL

Output:
    overall_risk_score   (0–100)
    risk_level           (LOW | MODERATE | HIGH | CRITICAL)
    component_scores     (dict per category)
    top_signals          (list of human-readable signals)
    triggered_rules      (list of rule IDs)
    explainability       (full evidence dict)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .rules import RuleEngine, RuleResult
from .features import engineer_mp_financial_features, engineer_project_features

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"
FEATURE_VERSION = "1.0.0"

# Default weights — configurable, NOT official government methodology
DEFAULT_WEIGHTS = {
    "financial": 0.30,
    "progress": 0.20,
    "timeline": 0.20,
    "rules": 0.15,
    "similarity": 0.10,
    "data_quality": 0.05,
}

RISK_THRESHOLDS = {
    "CRITICAL": 80,
    "HIGH": 60,
    "MODERATE": 30,
    "LOW": 0,
}


@dataclass
class RiskResult:
    """Complete risk assessment result for one entity."""
    entity_id: str
    entity_type: str  # 'mp' | 'project'

    # Scores
    overall_score: float
    risk_level: str

    # Component scores
    financial_risk: float = 0.0
    progress_risk: float = 0.0
    timeline_risk: float = 0.0
    rule_risk: float = 0.0
    similarity_risk: float = 0.0
    data_quality_risk: float = 0.0

    # Audit trail
    weights_used: Dict[str, float] = field(default_factory=dict)
    top_signals: List[Dict[str, Any]] = field(default_factory=list)
    triggered_rules: List[str] = field(default_factory=list)
    all_rule_results: List[RuleResult] = field(default_factory=list)

    # Explainability
    explanation: str = ""
    recommended_verification: List[str] = field(default_factory=list)

    # Versioning
    model_version: str = MODEL_VERSION
    feature_version: str = FEATURE_VERSION


def _score_to_risk_level(score: float) -> str:
    """Convert numeric score to risk tier string."""
    if score >= RISK_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif score >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif score >= RISK_THRESHOLDS["MODERATE"]:
        return "MODERATE"
    return "LOW"


class MPRiskEngine:
    """Risk engine for MP allocation records (real official data)."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.rule_engine = RuleEngine()

    def score(self, record: Dict) -> RiskResult:
        """
        Compute risk score for an MP allocation record.

        Uses:
        - Financial: anomaly_score from Isolation Forest
        - Data Quality: missing/invalid/duplicate flags
        - Rules: RULE-001, RULE-006, RULE-009, RULE-010
        - Progress/Timeline/Similarity: Not applicable for MP-level data
        """
        entity_id = str(record.get("id", record.get("sr_no", "unknown")))

        # ─── Financial Score ──────────────────────────────────────────────
        anomaly_score = record.get("anomaly_score", 0.0) or 0.0
        financial_risk = min(100.0, float(anomaly_score))

        # ─── Data Quality Score ────────────────────────────────────────────
        dq_score = 0.0
        if record.get("is_missing_amount"):
            dq_score += 50.0
        if record.get("is_invalid_amount"):
            dq_score += 40.0
        if record.get("is_duplicate_constituency"):
            dq_score += 30.0
        data_quality_risk = min(100.0, dq_score)

        # ─── Rule Engine ──────────────────────────────────────────────────
        rule_results = self.rule_engine.evaluate_mp_allocation(record)
        triggered = [r for r in rule_results if r.triggered]
        rule_risk = min(100.0, sum(r.contribution_score for r in triggered))
        triggered_rule_ids = [r.rule_id for r in triggered]

        # ─── Composite Score ──────────────────────────────────────────────
        w = self.weights
        overall_score = (
            financial_risk * w["financial"]
            + 0.0 * w["progress"]       # N/A for MP-level
            + 0.0 * w["timeline"]       # N/A for MP-level
            + rule_risk * w["rules"]
            + 0.0 * w["similarity"]     # N/A for MP-level
            + data_quality_risk * w["data_quality"]
        ) / (w["financial"] + w["rules"] + w["data_quality"])  # normalize by applicable weights

        overall_score = round(min(100.0, overall_score), 1)
        risk_level = _score_to_risk_level(overall_score)

        # ─── Top Signals ──────────────────────────────────────────────────
        top_signals = []
        if anomaly_score > 50:
            top_signals.append({
                "type": "financial_anomaly",
                "name": "High Anomaly Signal",
                "severity": "high" if anomaly_score > 70 else "medium",
                "description": f"Allocation amount is statistically unusual (Anomaly Signal: {anomaly_score:.0f}/100).",
                "evidence": {"anomaly_score": anomaly_score},
            })
        for r in triggered:
            top_signals.append({
                "type": "rule",
                "name": r.rule_name,
                "severity": r.severity,
                "description": r.description,
                "evidence": r.evidence,
            })
        if record.get("is_missing_amount"):
            top_signals.append({
                "type": "data_quality",
                "name": "Data Quality Issue",
                "severity": "medium",
                "description": "Allocation amount is missing in the official source.",
                "evidence": {"field": "allocated_amount_inr"},
            })

        # ─── Explanation ─────────────────────────────────────────────────
        mp = record.get("mp_name", "This MP")
        amount = record.get("allocated_amount_inr", 0)
        state = record.get("state", "")
        explanation = (
            f"{mp} ({state}) has an allocation of ₹{amount/1e7:.2f} Cr. "
            f"Overall Risk Signal: {overall_score}/100 ({risk_level}). "
        )
        if triggered:
            explanation += f"Triggered rules: {', '.join(r.rule_name for r in triggered)}."

        # ─── Verification Recommendations ────────────────────────────────
        recommended = []
        if overall_score >= 60:
            recommended = [
                "Verify allocation authorization documentation",
                "Review carry-forward balance from previous terms",
                "Cross-check with eSAKSHI portal project records",
            ]
        elif overall_score >= 30:
            recommended = [
                "Desk review of allocation basis",
                "Check for pending eSAKSHI project submissions",
            ]

        return RiskResult(
            entity_id=entity_id,
            entity_type="mp",
            overall_score=overall_score,
            risk_level=risk_level,
            financial_risk=financial_risk,
            data_quality_risk=data_quality_risk,
            rule_risk=rule_risk,
            weights_used=w,
            top_signals=top_signals[:5],  # top 5 signals
            triggered_rules=triggered_rule_ids,
            all_rule_results=rule_results,
            explanation=explanation,
            recommended_verification=recommended,
        )


class ProjectRiskEngine:
    """Risk engine for project records (demo data)."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.rule_engine = RuleEngine()

    def score(self, record: Dict) -> RiskResult:
        """Compute risk score for a project record."""
        entity_id = str(record.get("project_id", "unknown"))

        # ─── Financial Score ──────────────────────────────────────────────
        utilization = record.get("utilization_ratio", 0.0) or 0.0
        amount_zscore = abs(record.get("amount_zscore_vs_peers", 0.0) or 0.0)
        financial_risk = min(100.0, (amount_zscore * 20) + (max(0, utilization - 1.0) * 100))

        # ─── Progress Score ───────────────────────────────────────────────
        progress = record.get("physical_progress_pct", 0.0) or 0.0
        age = record.get("project_age_days", 0) or 0
        expected_progress = min(100.0, (age / 365.0) * 100.0)
        progress_gap = max(0, expected_progress - progress)
        progress_risk = min(100.0, progress_gap * 1.2)

        # ─── Timeline Score ───────────────────────────────────────────────
        delay_days = record.get("delay_days", 0) or 0
        timeline_risk = min(100.0, delay_days / 5.0)

        # ─── Similarity Score ─────────────────────────────────────────────
        # Not computed at this level (requires corpus comparison)
        similarity_risk = 0.0

        # ─── Rule Engine ──────────────────────────────────────────────────
        rule_results = self.rule_engine.evaluate_project(record)
        triggered = [r for r in rule_results if r.triggered]
        rule_risk = min(100.0, sum(r.contribution_score for r in triggered) / max(1, len(triggered)))
        triggered_rule_ids = [r.rule_id for r in triggered]

        # ─── Data Quality Score ────────────────────────────────────────────
        missing_critical = ["sanctioned_amount", "sanction_date", "work_category"]
        missing_count = sum(1 for f in missing_critical if not record.get(f))
        data_quality_risk = min(100.0, missing_count * 20.0)

        # ─── Composite Score ──────────────────────────────────────────────
        w = self.weights
        overall_score = (
            financial_risk * w["financial"]
            + progress_risk * w["progress"]
            + timeline_risk * w["timeline"]
            + rule_risk * w["rules"]
            + similarity_risk * w["similarity"]
            + data_quality_risk * w["data_quality"]
        )
        overall_score = round(min(100.0, overall_score), 1)
        risk_level = _score_to_risk_level(overall_score)

        # ─── Top Signals ──────────────────────────────────────────────────
        top_signals = []

        payment_gap = record.get("payment_progress_gap", 0.0) or 0.0
        if payment_gap > 30:
            top_signals.append({
                "type": "payment_progress_mismatch",
                "name": "Payment–Progress Mismatch",
                "severity": "critical" if payment_gap > 50 else "high",
                "description": (
                    f"Financial utilization ({record.get('financial_progress_pct', 0):.1f}%) "
                    f"is {payment_gap:.1f}% ahead of physical progress "
                    f"({record.get('physical_progress_pct', 0):.1f}%)."
                ),
                "evidence": {
                    "financial_progress_pct": record.get("financial_progress_pct"),
                    "physical_progress_pct": record.get("physical_progress_pct"),
                    "gap": payment_gap,
                },
            })

        if delay_days > 90:
            top_signals.append({
                "type": "timeline_risk",
                "name": "Timeline Risk",
                "severity": "critical" if delay_days > 365 else "high",
                "description": f"Project is delayed by {delay_days} days.",
                "evidence": {"delay_days": delay_days},
            })

        if progress_gap > 30:
            top_signals.append({
                "type": "progress_risk",
                "name": "Low Progress Signal",
                "severity": "high" if progress_gap > 50 else "medium",
                "description": (
                    f"Expected progress ~{expected_progress:.0f}% based on project age "
                    f"({age} days), but reported progress is only {progress:.1f}%."
                ),
                "evidence": {"expected_progress": expected_progress, "actual_progress": progress},
            })

        for r in triggered:
            top_signals.append({
                "type": "rule",
                "name": r.rule_name,
                "severity": r.severity,
                "description": r.description,
                "evidence": r.evidence,
            })

        # Deduplicate and limit to top 5
        seen = set()
        unique_signals = []
        for s in top_signals:
            key = s["name"]
            if key not in seen:
                seen.add(key)
                unique_signals.append(s)
        top_signals = unique_signals[:5]

        # ─── Explanation ─────────────────────────────────────────────────
        explanation = (
            f"Project '{record.get('work_description', '')[:60]}...' "
            f"in {record.get('district', '')} ({record.get('state', '')}) "
            f"has a risk signal of {overall_score}/100 ({risk_level}). "
        )
        if triggered_rule_ids:
            explanation += f"Rules triggered: {', '.join(triggered_rule_ids)}."

        # ─── Verification Recommendations ────────────────────────────────
        recommended = []
        if overall_score >= 60:
            recommended = [
                "Review sanction authorization and payment records",
                "Verify physical progress with field inspection",
                "Check for related/similar project records",
                "Review implementing agency documentation",
            ]
        elif overall_score >= 30:
            recommended = [
                "Desk review of progress reports",
                "Verify timeline and milestone records",
            ]

        return RiskResult(
            entity_id=entity_id,
            entity_type="project",
            overall_score=overall_score,
            risk_level=risk_level,
            financial_risk=financial_risk,
            progress_risk=progress_risk,
            timeline_risk=timeline_risk,
            rule_risk=rule_risk,
            similarity_risk=similarity_risk,
            data_quality_risk=data_quality_risk,
            weights_used=w,
            top_signals=top_signals,
            triggered_rules=triggered_rule_ids,
            all_rule_results=rule_results,
            explanation=explanation,
            recommended_verification=recommended,
        )
