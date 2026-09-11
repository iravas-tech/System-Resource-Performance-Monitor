"""
Simple resource forecasting for the monitoring project.

This is a deliberately understandable prediction model:
- take the most recent readings
- draw a best-fit line through them
- extend that line a few samples into the future

It is useful for short-term warnings, not long-term certainty.
"""

from datetime import timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


class ResourceForecaster:
    """Forecast short-term CPU, memory, and process-count movement."""

    def __init__(self, window: int = 60, periods_ahead: int = 6):
        self.window = window
        self.periods_ahead = periods_ahead

    def forecast(self, df: pd.DataFrame, column: str) -> Dict:
        """Return future values and a simple trend description for one metric."""
        if column not in df.columns or 'timestamp' not in df.columns:
            return {}

        values = pd.to_numeric(df[column], errors='coerce')
        valid = pd.DataFrame({'timestamp': df['timestamp'], 'value': values}).dropna()
        if len(valid) < 3:
            return {}

        recent = valid.tail(self.window).copy()
        timestamps = pd.to_datetime(recent['timestamp'])
        elapsed_seconds = (timestamps - timestamps.iloc[0]).dt.total_seconds().to_numpy()
        if elapsed_seconds[-1] <= 0:
            elapsed_seconds = np.arange(len(recent), dtype=float)

        model = LinearRegression()
        model.fit(elapsed_seconds.reshape(-1, 1), recent['value'].to_numpy())

        intervals = timestamps.diff().dt.total_seconds().dropna()
        sample_seconds = float(intervals.median()) if not intervals.empty else 5.0
        if not np.isfinite(sample_seconds) or sample_seconds <= 0:
            sample_seconds = 5.0

        future_seconds = elapsed_seconds[-1] + sample_seconds * np.arange(
            1, self.periods_ahead + 1,
            dtype=float
        )
        predictions = model.predict(future_seconds.reshape(-1, 1))

        if column == 'cpu_usage_percent':
            predictions = np.clip(predictions, 0, 100)
        else:
            predictions = np.maximum(predictions, 0)

        return {
            'metric': column,
            'current_value': float(recent['value'].iloc[-1]),
            'predictions': [float(value) for value in predictions],
            'future_timestamps': [
                (timestamps.iloc[-1] + timedelta(seconds=sample_seconds * index)).isoformat()
                for index in range(1, self.periods_ahead + 1)
            ],
            'slope_per_sample': float(model.coef_[0] * sample_seconds),
            'window_size': len(recent),
            'sample_seconds': sample_seconds,
        }

    def forecast_resources(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Forecast the main resources that the monitor collects."""
        forecasts = {}
        for column in ('cpu_usage_percent', 'memory_mb', 'process_count'):
            result = self.forecast(df, column)
            if result:
                forecasts[column] = result
        return forecasts
