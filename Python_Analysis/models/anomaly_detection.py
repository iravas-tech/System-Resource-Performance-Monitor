"""
Anomaly detection module for identifying unusual system behavior.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.covariance import EllipticEnvelope
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalies in system metrics."""

    def __init__(self, contamination: float = 0.05):
        """
        Initialize anomaly detector.

        Args:
            contamination: Expected fraction of outliers (0.0 to 0.5)
        """
        self.contamination = contamination
        self.isolation_forest = IsolationForest(contamination=contamination, random_state=42)
        self.elliptic_envelope = EllipticEnvelope(contamination=contamination, random_state=42)
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, features: List[str]) -> None:
        """
        Fit anomaly detection models.

        Args:
            df: Training data
            features: List of features to use
        """
        X = df[features].values

        # Fit models
        self.isolation_forest.fit(X)
        self.elliptic_envelope.fit(X)

        self.is_fitted = True
        logger.info(f"Fitted anomaly detection models on {len(df)} samples")

    def detect_isolation_forest(
        self,
        df: pd.DataFrame,
        features: List[str]
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect anomalies using Isolation Forest.

        Args:
            df: Data to check
            features: List of features to use

        Returns:
            Tuple of (DataFrame with anomaly flags, anomaly scores)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted, fitting now...")
            self.fit(df, features)

        X = df[features].values
        predictions = self.isolation_forest.predict(X)
        scores = self.isolation_forest.score_samples(X)

        # Convert predictions: -1 = anomaly, 1 = normal
        anomalies = (predictions == -1).astype(int)

        result_df = df.copy()
        result_df['anomaly_if'] = anomalies
        result_df['anomaly_score_if'] = -scores  # Invert so higher = more anomalous

        logger.info(f"Detected {anomalies.sum()} anomalies using Isolation Forest")
        return result_df, anomalies

    def detect_elliptic_envelope(
        self,
        df: pd.DataFrame,
        features: List[str]
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect anomalies using Elliptic Envelope (Mahalanobis distance).

        Args:
            df: Data to check
            features: List of features to use

        Returns:
            Tuple of (DataFrame with anomaly flags, anomaly scores)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted, fitting now...")
            self.fit(df, features)

        X = df[features].values
        predictions = self.elliptic_envelope.predict(X)
        distances = self.elliptic_envelope.mahalanobis(X)

        # Convert predictions: -1 = anomaly, 1 = normal
        anomalies = (predictions == -1).astype(int)

        result_df = df.copy()
        result_df['anomaly_ee'] = anomalies
        result_df['mahalanobis_distance'] = distances

        logger.info(f"Detected {anomalies.sum()} anomalies using Elliptic Envelope")
        return result_df, anomalies

    def detect_statistical(
        self,
        df: pd.DataFrame,
        feature: str,
        window: int = 10,
        std_threshold: float = 3.0
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect anomalies using rolling statistics.

        Args:
            df: Data to check
            feature: Feature to analyze
            window: Rolling window size
            std_threshold: Standard deviation threshold

        Returns:
            Tuple of (DataFrame with anomaly flags, anomaly indices)
        """
        df_copy = df.copy()

        # Calculate rolling mean and std
        rolling_mean = df_copy[feature].rolling(window=window, center=True).mean()
        rolling_std = df_copy[feature].rolling(window=window, center=True).std()

        # Calculate z-score
        z_scores = np.abs((df_copy[feature] - rolling_mean) / rolling_std)

        # Flag anomalies
        anomalies = (z_scores > std_threshold).astype(int)
        anomalies = anomalies.fillna(0).astype(int)

        df_copy['anomaly_statistical'] = anomalies
        df_copy[f'{feature}_z_score'] = z_scores

        logger.info(f"Detected {anomalies.sum()} anomalies using statistical method")
        return df_copy, anomalies.values

    def detect_cpu_spike(
        self,
        df: pd.DataFrame,
        threshold_percent: float = 80.0,
        duration_samples: int = 3
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect CPU usage spikes.

        Args:
            df: Data with cpu_usage_percent column
            threshold_percent: CPU usage threshold
            duration_samples: Minimum consecutive samples above threshold

        Returns:
            Tuple of (DataFrame with spike flags, spike indices)
        """
        df_copy = df.copy()

        # Identify high CPU periods
        high_cpu = df_copy['cpu_usage_percent'] > threshold_percent

        # Find consecutive sequences
        spikes = np.zeros(len(df_copy), dtype=int)
        consecutive = 0

        for i in range(len(high_cpu)):
            if high_cpu.iloc[i]:
                consecutive += 1
            else:
                if consecutive >= duration_samples:
                    # Mark the spike region
                    spikes[i - consecutive:i] = 1
                consecutive = 0

        # Handle case where spike extends to end of data
        if consecutive >= duration_samples:
            spikes[-consecutive:] = 1

        df_copy['cpu_spike'] = spikes

        logger.info(f"Detected {spikes.sum()} CPU spike samples")
        return df_copy, spikes
