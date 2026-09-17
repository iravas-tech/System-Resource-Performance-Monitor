"""
Data preprocessing module for system metrics.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import logging

logger = logging.getLogger(__name__)


class MetricsPreprocessor:
    """Preprocess system metrics for ML analysis."""

    def __init__(self):
        """Initialize preprocessor."""
        self.scaler_dict = {}
        self.mean_dict = {}
        self.std_dict = {}

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        method: str = 'forward_fill'
    ) -> pd.DataFrame:
        """
        Handle missing values in metrics.

        Args:
            df: DataFrame with metrics
            method: 'forward_fill', 'backward_fill', 'interpolate', or 'drop'

        Returns:
            DataFrame with missing values handled
        """
        df_copy = df.copy()

        if method == 'forward_fill':
            df_copy = df_copy.ffill().bfill()
        elif method == 'backward_fill':
            df_copy = df_copy.bfill().ffill()
        elif method == 'interpolate':
            # For numeric columns, interpolate
            numeric_cols = df_copy.select_dtypes(include=[np.number]).columns
            df_copy[numeric_cols] = df_copy[numeric_cols].interpolate(method='linear')
            df_copy = df_copy.bfill().ffill()
        elif method == 'drop':
            df_copy = df_copy.dropna()

        logger.info(f"Handled missing values using {method} method")
        return df_copy

    def normalize_features(
        self,
        df: pd.DataFrame,
        features: Optional[list] = None,
        method: str = 'standard'
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Normalize/scale features.

        Args:
            df: DataFrame with metrics
            features: List of columns to normalize
            method: 'standard' or 'minmax'

        Returns:
            Tuple of (normalized DataFrame, scaler parameters)
        """
        df_copy = df.copy()

        if features is None:
            features = df_copy.select_dtypes(include=[np.number]).columns.tolist()
            # Remove non-feature numeric columns
            if 'timestamp' in features:
                features.remove('timestamp')
            if 'process_id' in features:
                features.remove('process_id')
            for time_feature in ('hour', 'day_of_week', 'day_of_month', 'month', 'is_weekend'):
                if time_feature in features:
                    features.remove(time_feature)

        if method == 'standard':
            scaler = StandardScaler()
        else:  # minmax
            scaler = MinMaxScaler()

        df_copy[features] = scaler.fit_transform(df_copy[features])

        # Store scaler for later use
        for i, col in enumerate(features):
            self.scaler_dict[col] = scaler

        logger.info(f"Normalized {len(features)} features using {method} method")
        return df_copy, self.scaler_dict

    def remove_outliers(
        self,
        df: pd.DataFrame,
        features: Optional[list] = None,
        threshold: float = 3.0
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Remove outliers using Z-score method.

        Args:
            df: DataFrame with metrics
            features: List of columns to check for outliers
            threshold: Z-score threshold (default 3.0)

        Returns:
            Tuple of (DataFrame without outliers, mask of outliers)
        """
        df_copy = df.copy()

        if features is None:
            features = df_copy.select_dtypes(include=[np.number]).columns.tolist()

        # Calculate z-scores
        z_scores = np.abs((df_copy[features] - df_copy[features].mean()) / 
                          df_copy[features].std())

        # Find rows with any feature exceeding threshold
        outlier_mask = (z_scores > threshold).any(axis=1).values

        # Remove outliers
        df_copy = df_copy[~outlier_mask]

        logger.info(f"Removed {outlier_mask.sum()} outliers (threshold={threshold})")
        return df_copy, outlier_mask

    def create_time_features(
        self,
        df: pd.DataFrame,
        timestamp_col: str = 'timestamp'
    ) -> pd.DataFrame:
        """
        Create time-based features from timestamp.

        Args:
            df: DataFrame with metrics
            timestamp_col: Name of timestamp column

        Returns:
            DataFrame with new time features
        """
        df_copy = df.copy()

        if timestamp_col not in df_copy.columns:
            logger.warning(f"Timestamp column {timestamp_col} not found")
            return df_copy

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df_copy[timestamp_col]):
            df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])

        # Extract time features
        df_copy['hour'] = df_copy[timestamp_col].dt.hour
        df_copy['day_of_week'] = df_copy[timestamp_col].dt.dayofweek
        df_copy['day_of_month'] = df_copy[timestamp_col].dt.day
        df_copy['month'] = df_copy[timestamp_col].dt.month
        df_copy['is_weekend'] = df_copy['day_of_week'].isin([5, 6]).astype(int)

        logger.info("Created time-based features")
        return df_copy

    def create_rolling_features(
        self,
        df: pd.DataFrame,
        features: Optional[list] = None,
        windows: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Create rolling window features.

        Args:
            df: DataFrame with metrics
            features: List of columns to compute rolling stats for
            windows: List of window sizes (in rows)

        Returns:
            DataFrame with rolling features
        """
        df_copy = df.copy()

        if features is None:
            features = df_copy.select_dtypes(include=[np.number]).columns.tolist()

        if windows is None:
            windows = [5, 10, 30]  # 5, 10, 30 samples

        for col in features:
            for window in windows:
                if len(df_copy) >= window:
                    df_copy[f'{col}_rolling_mean_{window}'] = df_copy[col].rolling(window=window).mean()
                    df_copy[f'{col}_rolling_std_{window}'] = df_copy[col].rolling(window=window).std()

        logger.info(f"Created rolling features for windows: {windows}")
        return df_copy

    def prepare_for_ml(
        self,
        df: pd.DataFrame,
        remove_outliers: bool = True,
        normalize: bool = True,
        add_time_features: bool = True,
        add_rolling_features: bool = False
    ) -> pd.DataFrame:
        """
        Complete preprocessing pipeline.

        Args:
            df: Raw metrics DataFrame
            remove_outliers: Remove outliers
            normalize: Normalize features
            add_time_features: Add time-based features
            add_rolling_features: Add rolling window features

        Returns:
            Preprocessed DataFrame ready for ML
        """
        df_copy = df.copy()

        # Handle missing values
        df_copy = self.handle_missing_values(df_copy)

        # Remove outliers
        if remove_outliers:
            df_copy, _ = self.remove_outliers(df_copy)

        # Add time features
        if add_time_features:
            df_copy = self.create_time_features(df_copy)

        # Add rolling features
        if add_rolling_features:
            df_copy = self.create_rolling_features(df_copy)

        # Normalize features
        if normalize:
            df_copy, _ = self.normalize_features(df_copy)

        logger.info("Completed preprocessing pipeline")
        return df_copy

    def get_feature_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get statistics for numeric features.

        Args:
            df: DataFrame with metrics

        Returns:
            DataFrame with descriptive statistics
        """
        return df.describe().T
