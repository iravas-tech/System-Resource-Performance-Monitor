"""
Week 3 - real-time alerting.

This file checks the latest system data and asks:
    "Does anything look wrong right now?"

Simple flow:
1. read recent readings
2. clean the data a little
3. check CPU, memory, and process values
4. warn if something looks unusual
"""

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd

try:
    from .data_loader import MetricsDataLoader
    from .preprocessing import MetricsPreprocessor
    from .models.trend_analysis import TrendAnalyzer
    from .models.forecasting import ResourceForecaster
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import MetricsDataLoader
    from preprocessing import MetricsPreprocessor
    from models.trend_analysis import TrendAnalyzer
    from models.forecasting import ResourceForecaster

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """A simple rule that can trigger an alert."""

    name: str
    metric: str
    threshold: float
    severity: str = 'warning'
    direction: str = 'above'


class RealTimeAlertEngine:
    """Evaluate recent system health and detect anomalies in near real time."""

    def __init__(self, db_path: str = 'data/metrics.db'):
        self.db_path = db_path
        self.loader = MetricsDataLoader(db_path)
        self.preprocessor = MetricsPreprocessor()
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        self.alert_rules = [
            AlertRule('high_cpu', 'cpu_usage_percent', 80.0, 'high', 'above'),
            AlertRule('high_memory', 'memory_mb', 85.0, 'medium', 'above'),
            AlertRule('too_many_processes', 'process_count', 200.0, 'medium', 'above'),
            AlertRule('disk_pressure', 'disk_read_bytes', 100000000.0, 'high', 'above'),
        ]

    def _load_saved_models(self):
        """Load models trained by Week 2, if they are available."""
        model_files = {
            'isolation_forest': 'anomaly_isolation_forest.pkl',
            'lof': 'anomaly_lof.pkl',
            'scaler': 'scaler.pkl',
        }
        loaded = {}
        for name, filename in model_files.items():
            path = os.path.join(self.model_dir, filename)
            if os.path.exists(path):
                loaded[name] = joblib.load(path)
        return loaded

    def _saved_model_alert(self, df: pd.DataFrame) -> Dict | None:
        """Use the saved Week 2 models to evaluate recent readings."""
        models = self._load_saved_models()
        required_features = [
            'cpu_usage_percent',
            'memory_mb',
            'memory_available_mb',
            'disk_read_bytes',
            'disk_write_bytes',
            'network_bytes_sent',
            'network_bytes_recv',
            'process_count',
        ]
        if not all(name in models for name in ('isolation_forest', 'lof', 'scaler')):
            logger.warning('Saved Week 2 models are not available in %s', self.model_dir)
            return None

        available_features = [name for name in required_features if name in df.columns]
        if available_features != required_features:
            logger.warning('Recent data does not contain all trained model features')
            return None

        values = df[required_features].copy()
        values = values.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0)
        scaled_values = models['scaler'].transform(values)
        latest = scaled_values[-1:].copy()
        isolation_prediction = int(models['isolation_forest'].predict(latest)[0])
        lof_prediction = int(models['lof'].predict(latest)[0])

        if isolation_prediction != -1 and lof_prediction != -1:
            return None

        agreeing_models = sum(prediction == -1 for prediction in (isolation_prediction, lof_prediction))
        return {
            'type': 'trained_model_anomaly',
            'severity': 'high' if agreeing_models == 2 else 'medium',
            'message': (
                f'Saved Week 2 models flagged the latest reading as unusual '
                f'({agreeing_models}/2 models agree).'
            ),
            'value': agreeing_models,
            'timestamp': pd.Timestamp.now().isoformat(),
        }

    def _latest_process_context(self, hours: int = 24) -> str:
        """Return a short clue about the busiest recent process."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        if not self.loader.connect():
            return ''
        try:
            process_df = self.loader.load_process_metrics(start_time, end_time, top_n=1)
        finally:
            self.loader.disconnect()

        if process_df.empty:
            return ''
        latest_process = process_df.sort_values('timestamp').iloc[-1]
        return (
            f" Recent busiest process: {latest_process['process_name']} "
            f"({latest_process['memory_mb']:.0f} MB memory)."
        )

    def load_recent_data(self, hours: int = 24) -> pd.DataFrame:
        """Load the newest system readings from the database."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        if not self.loader.connect():
            logger.error('Could not connect to database for real-time alerting')
            return pd.DataFrame()

        try:
            df = self.loader.load_system_metrics(start_time, end_time)
            logger.info('Loaded %s rows for recent alert check', len(df))
            return df
        finally:
            self.loader.disconnect()

    def evaluate_recent_data(self, hours: int = 24) -> List[Dict]:
        """Check recent data and return warnings if the system looks unhealthy."""
        df = self.load_recent_data(hours)
        if df.empty:
            return []

        df_clean = self.preprocessor.prepare_for_ml(
            df,
            remove_outliers=False,
            normalize=False,
            add_time_features=True,
            add_rolling_features=True,
        )

        alerts: List[Dict] = []

        if 'cpu_usage_percent' in df_clean.columns:
            cpu_latest = float(df_clean['cpu_usage_percent'].iloc[-1])
            if cpu_latest > 80:
                alerts.append({
                    'type': 'high_cpu',
                    'severity': 'high',
                    'message': f'CPU usage is {cpu_latest:.1f}% and is above the safe threshold.',
                    'value': cpu_latest,
                    'timestamp': pd.Timestamp.now().isoformat()
                })

        if 'memory_available_mb' in df_clean.columns:
            memory_available_latest = float(df_clean['memory_available_mb'].iloc[-1])
            if memory_available_latest < 256:
                alerts.append({
                    'type': 'high_memory',
                    'severity': 'medium',
                    'message': f'Only {memory_available_latest:.0f} MB of memory is available, which may indicate pressure.',
                    'value': memory_available_latest,
                    'timestamp': pd.Timestamp.now().isoformat()
                })

        if 'process_count' in df_clean.columns:
            proc_latest = float(df_clean['process_count'].iloc[-1])
            process_threshold = float(df_clean['process_count'].quantile(0.95))
            if len(df_clean) >= 20 and proc_latest > process_threshold:
                alerts.append({
                    'type': 'too_many_processes',
                    'severity': 'medium',
                    'message': f'Process count has reached {proc_latest:.0f}, above this period\'s usual high point of {process_threshold:.0f}.',
                    'value': proc_latest,
                    'timestamp': pd.Timestamp.now().isoformat()
                })

        saved_alert = self._saved_model_alert(df_clean)
        if saved_alert:
            saved_alert['message'] += self._latest_process_context(hours)
            alerts.append(saved_alert)

        trend_analyzer = TrendAnalyzer()
        if 'cpu_usage_percent' in df_clean.columns:
            df_trend, trend_info = trend_analyzer.linear_regression_trend(
                df_clean,
                'cpu_usage_percent',
                window=max(10, min(100, len(df_clean)))
            )
            if trend_info:
                slope = float(trend_info.get('slope', 0.0))
                if abs(slope) > 0.3:
                    alerts.append({
                        'type': 'trend_shift',
                        'severity': 'medium',
                        'message': f'CPU trend is changing with slope {slope:.4f}, suggesting a sustained shift in workload.',
                        'value': slope,
                        'timestamp': pd.Timestamp.now().isoformat()
                    })

        forecasts = ResourceForecaster(window=60, periods_ahead=3).forecast_resources(df_clean)
        cpu_forecast = forecasts.get('cpu_usage_percent')
        if cpu_forecast and max(cpu_forecast['predictions']) >= 80:
            alerts.append({
                'type': 'forecast_high_cpu',
                'severity': 'medium',
                'message': (
                    f"The short-term CPU forecast reaches "
                    f"{max(cpu_forecast['predictions']):.1f}%, which may indicate rising workload."
                ),
                'value': max(cpu_forecast['predictions']),
                'timestamp': pd.Timestamp.now().isoformat()
            })

        return alerts

    def create_alert_summary(self, alerts: List[Dict]) -> str:
        """Turn alerts into plain English text that is easy to read."""
        if not alerts:
            return 'No alerts triggered. System behavior looks normal for the recent window.'

        lines = ['Recent alert summary:', '']
        for alert in alerts:
            lines.append(f"- [{alert['severity'].upper()}] {alert['message']}")
        return '\n'.join(lines)


def main():
    """Run a quick real-time check on recent data."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    engine = RealTimeAlertEngine(db_path='data/metrics.db')
    alerts = engine.evaluate_recent_data(hours=24)
    print(engine.create_alert_summary(alerts))


if __name__ == '__main__':
    main()
