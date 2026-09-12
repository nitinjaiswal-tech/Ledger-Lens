"""
Ledger Lens — Financial Anomaly Detection Engine

Uses Isolation Forest on engineered features from the real MP allocation dataset.

IMPORTANT:
- Output is called "Anomaly Signal" or "Anomaly Score", NEVER "fraud probability"
- Isolation Forest is unsupervised; no fraud labels exist for this dataset
- Results indicate statistical divergence, not confirmed wrongdoing

Model: Isolation Forest (sklearn)
Random State: 42 (reproducible)
Contamination: Configurable (default 0.05)
Persistence: models/isolation_forest_mp_v1.joblib
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from .features import engineer_mp_financial_features, build_isolation_forest_feature_matrix

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"
FEATURE_VERSION = "1.0.0"


class MPAllocationAnomalyDetector:
    """
    Isolation Forest-based anomaly detector for MP Allocation amounts.

    Produces a normalized Anomaly Signal score (0–100) per MP record.
    Higher score = more statistically unusual vs the peer distribution.
    This is NOT a fraud probability.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
        models_path: Optional[Path] = None,
    ):
        self.contamination = contamination
        self.random_state = random_state
        if models_path is not None:
            self.models_path = Path(models_path)
        else:
            try:
                from ..config import get_settings
                self.models_path = get_settings().models_path
            except Exception:
                self.models_path = Path("models")
        self.models_path.mkdir(parents=True, exist_ok=True)

        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[RobustScaler] = None
        self.feature_names: list = []
        self.is_fitted: bool = False

    @property
    def model_file(self) -> Path:
        return self.models_path / "isolation_forest_mp_v1.joblib"

    @property
    def meta_file(self) -> Path:
        return self.models_path / "isolation_forest_mp_v1_meta.json"

    def fit(self, df: pd.DataFrame) -> "MPAllocationAnomalyDetector":
        """
        Fit the Isolation Forest on the real MP allocation dataset.

        Pipeline:
        1. Feature engineering
        2. Robust scaling
        3. Isolation Forest fitting
        4. Model persistence
        """
        logger.info("Fitting MP Allocation Anomaly Detector...")

        # Step 1: Feature engineering
        engineered = engineer_mp_financial_features(df)

        # Step 2: Build feature matrix (only on rows with valid amounts)
        valid = engineered[engineered["allocated_amount_inr"] > 0].copy()
        X, feature_names = build_isolation_forest_feature_matrix(valid)

        if X.shape[0] < 10:
            logger.warning("Insufficient valid records for Isolation Forest fitting.")
            return self

        # Step 3: Robust scaling (handles outliers better than StandardScaler)
        self.scaler = RobustScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Step 4: Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=200,
            max_samples="auto",
        )
        self.model.fit(X_scaled)
        self.feature_names = feature_names
        self.is_fitted = True

        # Step 5: Persist model
        joblib.dump(
            {"model": self.model, "scaler": self.scaler, "feature_names": feature_names},
            self.model_file,
        )

        # Save metadata
        meta = {
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "n_samples_trained": int(X.shape[0]),
            "feature_names": feature_names,
            "description": (
                "Isolation Forest for MP allocation anomaly detection. "
                "Output is Anomaly Signal, NOT fraud probability."
            ),
        }
        with open(self.meta_file, "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Model fitted on {X.shape[0]} samples, {len(feature_names)} features.")
        return self

    def load(self) -> bool:
        """Load persisted model from disk."""
        if not self.model_file.exists():
            return False
        try:
            data = joblib.load(self.model_file)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data["feature_names"]
            self.is_fitted = True
            logger.info("Loaded persisted Isolation Forest model.")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute anomaly scores for MP allocation records.

        Returns the input DataFrame with added columns:
            anomaly_score        (0–100, higher = more unusual)
            is_financial_outlier (bool)
            anomaly_signal_label ("Normal" | "Unusual Signal" | "High Anomaly Signal")
        """
        if not self.is_fitted:
            loaded = self.load()
            if not loaded:
                logger.warning("Model not fitted/loaded. Returning unscored DataFrame.")
                df = df.copy()
                df["anomaly_score"] = 0.0
                df["is_financial_outlier"] = False
                df["anomaly_signal_label"] = "Not Scored"
                return df

        engineered = engineer_mp_financial_features(df)

        # Align feature columns
        available = [c for c in self.feature_names if c in engineered.columns]
        X = engineered[available].fillna(0).astype(float).values

        # Scale
        X_scaled = self.scaler.transform(X)

        # Isolation Forest scores: negative = anomalous, positive = normal
        raw_scores = self.model.decision_function(X_scaled)
        predictions = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal

        # Normalize to 0–100 (flip so higher = more anomalous)
        normalized = 100 * (1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10))
        normalized = np.clip(normalized, 0, 100)

        result = df.copy()
        result["anomaly_score"] = np.round(normalized, 2)
        result["is_financial_outlier"] = predictions == -1

        # Human-readable signal label
        conditions = [
            normalized >= 75,
            normalized >= 50,
            normalized >= 0,
        ]
        labels = ["High Anomaly Signal", "Unusual Signal", "Normal"]
        result["anomaly_signal_label"] = np.select(conditions, labels, default="Normal")

        return result

    def get_feature_contributions(self, df: pd.DataFrame) -> Dict:
        """
        Approximate feature contributions for explainability.
        Uses per-feature deviation from median as a proxy contribution.
        """
        engineered = engineer_mp_financial_features(df)
        available = [c for c in self.feature_names if c in engineered.columns]
        vals = engineered[available].fillna(0).astype(float)

        contributions = {}
        for col in available:
            median_val = float(vals[col].median())
            deviation = abs(float(vals[col].iloc[0]) - median_val) if len(vals) == 1 else float(vals[col].std())
            contributions[col] = round(deviation, 4)

        return contributions


def run_mp_anomaly_detection(
    df: pd.DataFrame,
    contamination: float = 0.05,
    models_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Convenience function: fit (or load) and predict anomaly scores on the MP dataset.

    Args:
        df: Cleaned MP allocation DataFrame (real official data)
        contamination: Fraction of expected anomalies (default 0.05)
        models_path: Directory for model persistence

    Returns:
        DataFrame with anomaly scores added.
    """
    detector = MPAllocationAnomalyDetector(
        contamination=contamination,
        models_path=models_path,
    )

    # Try loading existing model, else fit fresh
    if not detector.load():
        detector.fit(df)

    return detector.predict(df)
