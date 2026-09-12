"""
Ledger Lens — Rule Engine

Deterministic rule-based checks that run independently from ML models.
Rules are configurable, auditable, and provide clear evidence for each trigger.

Each rule returns:
    rule_id, rule_name, severity, description, evidence, affected_fields

Rules operate on available data. Rules requiring unavailable data are gracefully skipped.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


@dataclass
class RuleResult:
    """Result from a single rule evaluation."""
    rule_id: str
    rule_name: str
    severity: str  # "low" | "medium" | "high" | "critical"
    triggered: bool
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    affected_fields: List[str] = field(default_factory=list)
    contribution_score: float = 0.0  # 0-100


# Configurable thresholds
DEFAULT_THRESHOLDS = {
    "high_expenditure_low_progress_gap": 30.0,       # % gap to trigger payment-progress mismatch
    "critical_expenditure_low_progress_gap": 50.0,    # % gap for critical severity
    "utilization_overrun_threshold": 1.05,            # 105%+ expenditure vs sanction
    "severely_delayed_days": 365,                     # Days delay for severe classification
    "delayed_days": 90,                               # Days delay for normal classification
    "stagnation_age_days": 365,                       # Project age to check stagnation
    "stagnation_progress_threshold": 30.0,            # Progress % below which stagnation triggers
    "high_amount_zscore": 2.0,                        # Z-score threshold for high amount flag
    "missing_data_fields_threshold": 2,               # Number of missing critical fields to flag
    "peer_deviation_threshold_pct": 50.0,             # % deviation from peer to flag
}


class RuleEngine:
    """Configurable, auditable rule engine for MPLADS risk analysis."""

    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def evaluate_mp_allocation(self, record: Dict) -> List[RuleResult]:
        """
        Evaluate all applicable rules for an MP allocation record.
        Only runs rules supported by the available data.

        Args:
            record: Dict with keys from MPAllocation model

        Returns:
            List of RuleResult for each triggered rule.
        """
        results = []

        results.append(self._rule_001_high_allocation_outlier(record))
        results.append(self._rule_006_missing_data(record))
        results.append(self._rule_009_duplicate_constituency(record))
        results.append(self._rule_010_state_peer_deviation(record))

        return [r for r in results if r is not None]

    def evaluate_project(self, record: Dict) -> List[RuleResult]:
        """
        Evaluate all applicable rules for a project record.

        Args:
            record: Dict with keys from Project model

        Returns:
            List of RuleResult for each triggered rule.
        """
        results = []

        results.append(self._rule_002_high_utilization(record))
        results.append(self._rule_003_payment_progress_mismatch(record))
        results.append(self._rule_004_severe_delay(record))
        results.append(self._rule_005_progress_stagnation(record))
        results.append(self._rule_006_missing_data_project(record))
        results.append(self._rule_007_overutilization(record))
        results.append(self._rule_008_long_duration_no_completion(record))

        return [r for r in results if r is not None]

    # ─── MP Allocation Rules ─────────────────────────────────────────────────

    def _rule_001_high_allocation_outlier(self, r: Dict) -> Optional[RuleResult]:
        """RULE-001: Unusually high allocation amount relative to peers."""
        amount = r.get("allocated_amount_inr", 0.0) or 0.0
        zscore = r.get("allocation_zscore")
        state_dev = r.get("state_peer_deviation_pct")

        if zscore is None:
            return None

        threshold = self.thresholds["high_amount_zscore"]
        triggered = abs(zscore) > threshold

        severity = "low"
        if abs(zscore) > 3.5:
            severity = "critical"
        elif abs(zscore) > 2.5:
            severity = "high"
        elif abs(zscore) > threshold:
            severity = "medium"

        direction = "above" if zscore > 0 else "below"

        return RuleResult(
            rule_id="RULE-001",
            rule_name="Allocation Amount Outlier",
            severity=severity,
            triggered=triggered,
            description=(
                f"MP allocation of ₹{amount/1e7:.2f} Cr is {abs(zscore):.1f} standard deviations "
                f"{direction} the national mean. "
                + (f"This is {abs(state_dev):.1f}% {direction} state peer average." if state_dev else "")
            ),
            evidence={
                "allocated_amount_inr": amount,
                "zscore": round(zscore, 3),
                "state_peer_deviation_pct": round(state_dev, 2) if state_dev else None,
                "threshold_zscore": threshold,
            },
            affected_fields=["allocated_amount_inr"],
            contribution_score=min(100, abs(zscore) * 20),
        )

    def _rule_006_missing_data(self, r: Dict) -> Optional[RuleResult]:
        """RULE-006: Missing critical allocation amount."""
        is_missing = r.get("is_missing_amount", False)
        if not is_missing:
            return RuleResult(
                rule_id="RULE-006",
                rule_name="Missing Allocation Amount",
                severity="low",
                triggered=False,
                description="No missing critical data.",
                evidence={},
                affected_fields=[],
            )
        return RuleResult(
            rule_id="RULE-006",
            rule_name="Missing Allocation Amount",
            severity="medium",
            triggered=True,
            description=(
                "Allocation amount is missing or unrecorded in the official source. "
                "This may indicate a pending entry or data entry gap requiring verification."
            ),
            evidence={"is_missing_amount": True},
            affected_fields=["allocated_amount_inr"],
            contribution_score=40.0,
        )

    def _rule_009_duplicate_constituency(self, r: Dict) -> Optional[RuleResult]:
        """RULE-009: Constituency appears more than once in dataset."""
        is_dup = r.get("is_duplicate_constituency", False)
        constituency = r.get("constituency_clean", "")
        return RuleResult(
            rule_id="RULE-009",
            rule_name="Duplicate Constituency Record",
            severity="medium" if is_dup else "low",
            triggered=is_dup,
            description=(
                f"Constituency '{constituency}' appears more than once in the dataset. "
                "This may reflect a by-election or seat transition requiring verification."
                if is_dup
                else "No duplicate constituency issue."
            ),
            evidence={"constituency": constituency, "is_duplicate_constituency": is_dup},
            affected_fields=["constituency"] if is_dup else [],
            contribution_score=30.0 if is_dup else 0.0,
        )

    def _rule_010_state_peer_deviation(self, r: Dict) -> Optional[RuleResult]:
        """RULE-010: Allocation significantly deviates from state peer group."""
        state_dev = r.get("state_peer_deviation_pct")
        amount = r.get("allocated_amount_inr", 0.0) or 0.0
        state = r.get("state", "")

        if state_dev is None or amount == 0:
            return None

        threshold = self.thresholds["peer_deviation_threshold_pct"]
        triggered = abs(state_dev) > threshold

        direction = "above" if state_dev > 0 else "below"
        severity = "high" if abs(state_dev) > 80 else ("medium" if triggered else "low")

        return RuleResult(
            rule_id="RULE-010",
            rule_name="State Peer Group Deviation",
            severity=severity,
            triggered=triggered,
            description=(
                f"Allocation is {abs(state_dev):.1f}% {direction} the {state} state average. "
                f"This is a significant deviation from the peer group baseline."
                if triggered
                else f"Allocation is within {abs(state_dev):.1f}% of state peer average."
            ),
            evidence={
                "allocated_amount_inr": amount,
                "state_peer_deviation_pct": round(state_dev, 2),
                "state": state,
                "threshold_pct": threshold,
            },
            affected_fields=["allocated_amount_inr", "state"],
            contribution_score=min(100, abs(state_dev) * 0.8) if triggered else 0.0,
        )

    # ─── Project Rules ────────────────────────────────────────────────────────

    def _rule_002_high_utilization(self, r: Dict) -> Optional[RuleResult]:
        """RULE-002: Unusually high expenditure relative to project category peers."""
        amount_zscore = r.get("amount_zscore_vs_peers", 0.0) or 0.0
        sanctioned = r.get("sanctioned_amount", 0.0) or 0.0
        category = r.get("work_category", "")
        triggered = amount_zscore > 2.0

        return RuleResult(
            rule_id="RULE-002",
            rule_name="Unusually High Project Amount vs Peers",
            severity="high" if amount_zscore > 3.0 else ("medium" if triggered else "low"),
            triggered=triggered,
            description=(
                f"Project sanctioned amount (₹{sanctioned/1e5:.1f}L) is "
                f"{amount_zscore:.1f} standard deviations above the '{category}' category average."
                if triggered
                else "Project amount is within normal peer range."
            ),
            evidence={
                "sanctioned_amount": sanctioned,
                "amount_zscore_vs_peers": round(amount_zscore, 3),
                "work_category": category,
            },
            affected_fields=["sanctioned_amount"],
            contribution_score=min(100, amount_zscore * 25) if triggered else 0.0,
        )

    def _rule_003_payment_progress_mismatch(self, r: Dict) -> Optional[RuleResult]:
        """RULE-004: Payment–Progress Mismatch."""
        fin_pct = r.get("financial_progress_pct")
        phys_pct = r.get("physical_progress_pct")

        if fin_pct is None or phys_pct is None:
            return None

        gap = fin_pct - phys_pct
        high_thresh = self.thresholds["high_expenditure_low_progress_gap"]
        critical_thresh = self.thresholds["critical_expenditure_low_progress_gap"]

        triggered = gap > high_thresh
        severity = "critical" if gap > critical_thresh else ("high" if triggered else "low")

        return RuleResult(
            rule_id="RULE-004",
            rule_name="Payment–Progress Mismatch",
            severity=severity,
            triggered=triggered,
            description=(
                f"Financial utilization ({fin_pct:.1f}%) is {gap:.1f} percentage points "
                f"ahead of physical progress ({phys_pct:.1f}%). "
                "This pattern requires verification of payment authorization and milestone completion."
                if triggered
                else f"Payment ({fin_pct:.1f}%) and progress ({phys_pct:.1f}%) are consistent."
            ),
            evidence={
                "financial_progress_pct": fin_pct,
                "physical_progress_pct": phys_pct,
                "gap": round(gap, 1),
                "threshold": high_thresh,
            },
            affected_fields=["financial_progress_pct", "physical_progress_pct", "expenditure_amount"],
            contribution_score=min(100, gap * 1.5) if triggered else 0.0,
        )

    def _rule_004_severe_delay(self, r: Dict) -> Optional[RuleResult]:
        """RULE-003: Project delay classification."""
        delay_days = r.get("delay_days", 0) or 0
        project_id = r.get("project_id", "")

        severe_thresh = self.thresholds["severely_delayed_days"]
        normal_thresh = self.thresholds["delayed_days"]

        if delay_days > severe_thresh:
            triggered = True
            severity = "critical"
            desc = f"Project is severely delayed by {delay_days} days (>{severe_thresh} days threshold)."
            score = min(100, 60 + delay_days / 20)
        elif delay_days > normal_thresh:
            triggered = True
            severity = "high"
            desc = f"Project is delayed by {delay_days} days (>{normal_thresh} days threshold)."
            score = min(80, 30 + delay_days / 10)
        elif delay_days > 0:
            triggered = False
            severity = "low"
            desc = f"Project is {delay_days} days past expected completion (Watch period)."
            score = 0.0
        else:
            triggered = False
            severity = "low"
            desc = "Project is on schedule."
            score = 0.0

        return RuleResult(
            rule_id="RULE-003",
            rule_name="Timeline Delay",
            severity=severity,
            triggered=triggered,
            description=desc,
            evidence={"delay_days": delay_days, "threshold_severe": severe_thresh},
            affected_fields=["delay_days", "expected_completion_date"],
            contribution_score=score,
        )

    def _rule_005_progress_stagnation(self, r: Dict) -> Optional[RuleResult]:
        """RULE-005: Progress stagnation — project is old but progress is very low."""
        age = r.get("project_age_days", 0) or 0
        progress = r.get("physical_progress_pct", 0.0) or 0.0
        age_thresh = self.thresholds["stagnation_age_days"]
        prog_thresh = self.thresholds["stagnation_progress_threshold"]

        triggered = (age > age_thresh) and (progress < prog_thresh)

        return RuleResult(
            rule_id="RULE-005",
            rule_name="Progress Stagnation",
            severity="high" if triggered else "low",
            triggered=triggered,
            description=(
                f"Project is {age} days old but shows only {progress:.1f}% physical progress. "
                "Timeline and progress pattern requires verification."
                if triggered
                else f"Progress is consistent with project age ({age} days, {progress:.1f}%)."
            ),
            evidence={
                "project_age_days": age,
                "physical_progress_pct": progress,
                "threshold_age_days": age_thresh,
                "threshold_progress_pct": prog_thresh,
            },
            affected_fields=["physical_progress_pct", "project_age_days"],
            contribution_score=60.0 if triggered else 0.0,
        )

    def _rule_006_missing_data_project(self, r: Dict) -> Optional[RuleResult]:
        """RULE-006: Missing critical project information."""
        critical_fields = ["sanctioned_amount", "sanction_date", "work_category", "implementing_agency"]
        missing = [f for f in critical_fields if not r.get(f)]
        triggered = len(missing) >= self.thresholds["missing_data_fields_threshold"]

        return RuleResult(
            rule_id="RULE-006",
            rule_name="Missing Critical Project Information",
            severity="medium" if triggered else "low",
            triggered=triggered,
            description=(
                f"Project record is missing {len(missing)} critical fields: {', '.join(missing)}. "
                "Incomplete records reduce monitoring reliability."
                if triggered
                else "Project record has all critical fields present."
            ),
            evidence={"missing_fields": missing, "count": len(missing)},
            affected_fields=missing,
            contribution_score=15.0 * len(missing) if triggered else 0.0,
        )

    def _rule_007_overutilization(self, r: Dict) -> Optional[RuleResult]:
        """RULE-007: Expenditure exceeds sanctioned amount."""
        utilization = r.get("utilization_ratio", 0.0) or 0.0
        sanctioned = r.get("sanctioned_amount", 0.0) or 0.0
        expenditure = r.get("expenditure_amount", 0.0) or 0.0
        threshold = self.thresholds["utilization_overrun_threshold"]

        triggered = utilization > threshold

        return RuleResult(
            rule_id="RULE-007",
            rule_name="Expenditure Overrun",
            severity="critical" if utilization > 1.15 else ("high" if triggered else "low"),
            triggered=triggered,
            description=(
                f"Recorded expenditure (₹{expenditure/1e5:.1f}L) exceeds sanctioned amount "
                f"(₹{sanctioned/1e5:.1f}L) by {(utilization-1)*100:.1f}%. "
                "This requires authorization verification."
                if triggered
                else f"Expenditure ({utilization*100:.1f}% of sanction) is within bounds."
            ),
            evidence={
                "utilization_ratio": round(utilization, 4),
                "sanctioned_amount": sanctioned,
                "expenditure_amount": expenditure,
                "threshold": threshold,
            },
            affected_fields=["expenditure_amount", "utilization_ratio"],
            contribution_score=min(100, (utilization - 1) * 500) if triggered else 0.0,
        )

    def _rule_008_long_duration_no_completion(self, r: Dict) -> Optional[RuleResult]:
        """RULE-008: Long-running project with no completion."""
        age = r.get("project_age_days", 0) or 0
        status = r.get("status", "")
        progress = r.get("physical_progress_pct", 0.0) or 0.0
        completed = r.get("actual_completion_date")

        triggered = (age > 1460) and (not completed) and (status not in ["Completed"])

        return RuleResult(
            rule_id="RULE-008",
            rule_name="Extended Duration Without Completion",
            severity="high" if triggered else "low",
            triggered=triggered,
            description=(
                f"Project has been running for {age} days (over 4 years) without completion. "
                f"Current reported progress: {progress:.1f}%."
                if triggered
                else f"Project age ({age} days) is within normal bounds."
            ),
            evidence={
                "project_age_days": age,
                "status": status,
                "physical_progress_pct": progress,
                "actual_completion_date": completed,
            },
            affected_fields=["project_age_days", "status", "actual_completion_date"],
            contribution_score=70.0 if triggered else 0.0,
        )
