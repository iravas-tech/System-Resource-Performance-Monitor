"""
Trend analysis module for forecasting and temporal patterns.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, List
from sklearn.linear_model import LinearRegression
import logging

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyze trends and patterns in system metrics over time."""

    def __init__(self):
        """Initialize trend analyzer."""
        self.trend_models = {}

    def calculate_trend(
        self,
        df: pd.DataFrame,
        column: str,
        window: int = 10
    ) -> pd.DataFrame:
        """
        Calculate trend line for a metric.

        Args:
            df: DataFrame with metrics
            column: Column to analyze
            window: Window size for trend calculation

        Returns:
            DataFrame with trend column added
        """
        df_copy = df.copy()

        if len(df) < window:
            logger.warning(f"Not enough data to calculate trend (need {window}, have {len(df)})")
            return df_copy

        # Calculate simple moving average
        df_copy[f'{column}_trend'] = df[column].rolling(window=window).mean()

        logger.info(f"Calculated trend for {column} with window size {window}")
        return df_copy

    def linear_regression_trend(
        self,
        df: pd.DataFrame,
        column: str,
        window: int = 100
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Fit linear regression trend lines.

        Args:
            df: DataFrame with metrics
            column: Column to analyze
            window: Window size for regression

        Returns:
            Tuple of (DataFrame with trend, model info)
        """
        df_copy = df.copy()

        if len(df) < window:
            logger.warning(f"Not enough data for linear regression")
            return df_copy, {}

        # Fit linear regression on last 'window' samples
        X = np.arange(len(df) - window, len(df)).reshape(-1, 1)
        y = df[column].iloc[-window:].values

        model = LinearRegression()
        model.fit(X, y)

        # Calculate trend
        X_full = np.arange(len(df)).reshape(-1, 1)
        trend = model.predict(X_full)

        df_copy[f'{column}_regression_trend'] = trend

        model_info = {
            'slope': model.coef_[0],
            'intercept': model.intercept_,
            'r_squared': model.score(X, y)
        }

        logger.info(f"Linear regression trend - slope: {model_info['slope']:.4f}, "
                   f"R²: {model_info['r_squared']:.4f}")

        return df_copy, model_info

    def detect_trend_change(
        self,
        df: pd.DataFrame,
        column: str,
        window1: int = 10,
        window2: int = 20,
        threshold: float = 0.05
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect when trend changes significantly.

        Args:
            df: DataFrame with metrics
            column: Column to analyze
            window1: Short-term window
            window2: Long-term window
            threshold: Relative change threshold

        Returns:
            Tuple of (DataFrame with change flags, change indices)
        """
        df_copy = df.copy()

        # Calculate moving averages
        ma_short = df[column].rolling(window=window1).mean()
        ma_long = df[column].rolling(window=window2).mean()

        # Calculate relative change
        relative_change = np.abs((ma_short - ma_long) / ma_long)

        # Flag significant changes
        changes = (relative_change > threshold).astype(int)

        df_copy['trend_change'] = changes
        df_copy['trend_change_magnitude'] = relative_change

        n_changes = changes.sum()
        logger.info(f"Detected {n_changes} trend changes in {column}")

        return df_copy, changes.values

    def forecast_simple_exponential(
        self,
        df: pd.DataFrame,
        column: str,
        alpha: float = 0.3,
        periods_ahead: int = 10
    ) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Simple exponential smoothing forecast.

        Args:
            df: DataFrame with metrics
            column: Column to forecast
            alpha: Smoothing factor (0 to 1)
            periods_ahead: Number of periods to forecast

        Returns:
            Tuple of (forecast array, DataFrame with smoothed values)
        """
        df_copy = df.copy()

        values = df[column].values
        smoothed = np.zeros_like(values, dtype=float)

        # Initialize
        smoothed[0] = values[0]

        # Apply exponential smoothing
        for i in range(1, len(values)):
            smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i - 1]

        # Forecast
        forecast = np.zeros(periods_ahead)
        last_smoothed = smoothed[-1]

        for i in range(periods_ahead):
            forecast[i] = last_smoothed

        df_copy[f'{column}_smoothed'] = smoothed

        logger.info(f"Exponential smoothing forecast ({periods_ahead} periods ahead)")
        return forecast, df_copy

    def calculate_seasonality(
        self,
        df: pd.DataFrame,
        column: str,
        period: int = 24
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Calculate seasonal components.

        Args:
            df: DataFrame with metrics and 'hour' column
            column: Column to analyze
            period: Seasonal period (e.g., 24 for daily hourly pattern)

        Returns:
            Tuple of (DataFrame with seasonality, seasonal factors)
        """
        df_copy = df.copy()

        if 'hour' not in df_copy.columns:
            logger.warning("'hour' column required for seasonality analysis")
            return df_copy, np.array([])

        # Calculate average for each hour
        hourly_avg = df.groupby('hour')[column].mean()
        overall_avg = df[column].mean()

        # Seasonal factors
        seasonal_factors = (hourly_avg / overall_avg).values

        # Add seasonal component back to dataframe
        df_copy['seasonal_component'] = df_copy['hour'].map(
            lambda h: seasonal_factors[h] if h < len(seasonal_factors) else 1.0
        )

        logger.info(f"Calculated seasonality for {column} with period {period}")
        return df_copy, seasonal_factors

    def anomaly_from_forecast(
        self,
        df: pd.DataFrame,
        column: str,
        window: int = 20,
        threshold: float = 2.0
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Detect anomalies based on deviation from exponential smoothing forecast.

        Args:
            df: DataFrame with metrics
            column: Column to analyze
            window: Window size for smoothing
            threshold: Standard deviation threshold

        Returns:
            Tuple of (DataFrame with anomaly flags, anomaly indices)
        """
        df_copy = df.copy()

        # Exponential smoothing
        values = df[column].values
        alpha = 2 / (window + 1)

        smoothed = np.zeros_like(values, dtype=float)
        smoothed[0] = values[0]

        for i in range(1, len(values)):
            smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i - 1]

        # Calculate residuals
        residuals = values - smoothed

        # Calculate rolling std of residuals
        residual_std = pd.Series(residuals).rolling(window=window).std()
        residual_std = residual_std.fillna(residual_std.mean())

        # Detect anomalies
        anomalies = (np.abs(residuals) > threshold * residual_std).astype(int)

        df_copy['forecast_anomaly'] = anomalies
        df_copy[f'{column}_forecast'] = smoothed

        logger.info(f"Detected {anomalies.sum()} forecast-based anomalies")
        return df_copy, anomalies
