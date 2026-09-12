"""Unit and integration tests for the ML pipeline and risk engine.
Compatible with standard library unittest.
"""

import unittest
import numpy as np
import pandas as pd
from pathlib import Path

from app.data.cleaner import DataCleaner
from app.ml.features import engineer_mp_financial_features, build_isolation_forest_feature_matrix
from app.ml.financial_anomaly import MPAllocationAnomalyDetector, run_mp_anomaly_detection
from app.ml.rules import RuleEngine, RuleResult
from app.ml.risk_engine import MPRiskEngine, ProjectRiskEngine


class TestMLPipeline(unittest.TestCase):
    """Test suite for feature engineering, anomaly detection, and risk scoring."""

    @classmethod
    def setUpClass(cls):
        cleaner = DataCleaner()
        cls.cleaned_df, _ = cleaner.process_mp_allocations()

    def test_feature_engineering(self):
        """Test feature engineering generates required features."""
        engineered = engineer_mp_financial_features(self.cleaned_df)
        self.assertIn("allocation_zscore", engineered.columns)
        self.assertIn("state_peer_deviation_pct", engineered.columns)
        self.assertIn("allocation_percentile", engineered.columns)

    def test_isolation_forest_detector_load_and_predict(self):
        """Test loading persisted Isolation Forest model and predicting anomaly scores."""
        detector = MPAllocationAnomalyDetector()
        loaded = detector.load()
        self.assertTrue(loaded, "Failed to load pre-trained Isolation Forest model")

        # Run prediction on cleaned dataset
        results = detector.predict(self.cleaned_df)

        self.assertIn("anomaly_score", results.columns)
        self.assertIn("is_financial_outlier", results.columns)
        self.assertIn("anomaly_signal_label", results.columns)

        # Verify scores are bounded within [0, 100]
        scores = results["anomaly_score"]
        self.assertTrue((scores >= 0).all() and (scores <= 100).all())

        # Verify labels match score criteria
        high_signals = results[results["anomaly_score"] >= 75]
        for _, row in high_signals.iterrows():
            self.assertEqual(row["anomaly_signal_label"], "High Anomaly Signal")

    def test_rule_engine_evaluations(self):
        """Test rule engine detection on specific records."""
        rule_engine = RuleEngine()
        
        # Test record with missing amount
        missing_record = {
            "mp_name": "TEST MP",
            "constituency": "TEST CONST",
            "allocated_amount_inr": None,
            "is_missing_amount": True,
            "is_duplicate_constituency": False,
        }
        signals = rule_engine.evaluate_mp_allocation(missing_record)
        triggered_codes = [s.rule_id for s in signals if s.triggered]
        self.assertIn("RULE-006", triggered_codes)

        # Test duplicate constituency record
        dup_record = {
            "mp_name": "TEST MP 2",
            "constituency": "NANDED",
            "allocated_amount_inr": 1000000.0,
            "is_missing_amount": False,
            "is_duplicate_constituency": True,
        }
        signals_dup = rule_engine.evaluate_mp_allocation(dup_record)
        triggered_codes_dup = [s.rule_id for s in signals_dup if s.triggered]
        self.assertIn("RULE-009", triggered_codes_dup)

    def test_mp_risk_engine(self):
        """Test composite risk score calculation for MP allocations."""
        mp_engine = MPRiskEngine()
        
        record = {
            "sr_no": 1,
            "state": "MAHARASHTRA",
            "mp_name": "TEST MP",
            "constituency": "TEST",
            "allocated_amount_inr": 147000000.0,
            "allocation_zscore": 0.5,
            "state_peer_deviation_pct": 10.0,
            "anomaly_score": 25.0,
            "is_financial_outlier": False,
            "is_missing_amount": False,
            "is_duplicate_constituency": False,
            "is_data_quality_issue": False,
        }
        result = mp_engine.score(record)

        self.assertIsInstance(result.overall_score, float)
        self.assertIn(result.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertTrue(0 <= result.overall_score <= 100)


if __name__ == "__main__":
    unittest.main()
