"""
Week 4 - dashboard and report builder.

This file turns raw numbers into a simple picture and a short summary.
The goal is to help someone understand the machine quickly.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

try:
    from .data_loader import MetricsDataLoader
    from .models.forecasting import ResourceForecaster
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import MetricsDataLoader
    from models.forecasting import ResourceForecaster

logger = logging.getLogger(__name__)


class DashboardReportGenerator:
    """Build a simple dashboard and summary report from recent metrics."""

    def __init__(self, db_path: str = 'data/metrics.db', output_dir: str = 'reports/'):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def load_recent_metrics(self, hours: int = 24) -> pd.DataFrame:
        """Load recent system metrics."""
        loader = MetricsDataLoader(self.db_path)
        if not loader.connect():
            return pd.DataFrame()

        try:
            end_time = datetime.now()
            start_time = end_time - pd.Timedelta(hours=hours)
            return loader.load_system_metrics(start_time, end_time)
        finally:
            loader.disconnect()

    def create_dashboard(self, df: pd.DataFrame, output_path: Optional[str] = None) -> str:
        """Make one chart image showing the main system health values."""
        if df.empty:
            raise ValueError('No metrics available for dashboard generation.')

        if output_path is None:
            output_path = os.path.join(self.output_dir, 'system_dashboard.png')

        output_directory = os.path.dirname(output_path)
        if output_directory:
            os.makedirs(output_directory, exist_ok=True)

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('System Resource Monitor Dashboard', fontsize=18, fontweight='bold')

        axes[0, 0].plot(df['timestamp'], df['cpu_usage_percent'], color='tab:blue', linewidth=2)
        axes[0, 0].set_title('CPU Usage')
        axes[0, 0].set_ylabel('%')
        axes[0, 0].grid(alpha=0.3)

        axes[0, 1].plot(df['timestamp'], df['memory_mb'], color='tab:orange', linewidth=2)
        axes[0, 1].set_title('Memory Usage')
        axes[0, 1].set_ylabel('MB')
        axes[0, 1].grid(alpha=0.3)

        axes[1, 0].plot(df['timestamp'], df['process_count'], color='tab:red', linewidth=2)
        axes[1, 0].set_title('Processes Running')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].grid(alpha=0.3)

        dashboard_data = df.copy()
        if 'hour' not in dashboard_data.columns:
            dashboard_data['hour'] = dashboard_data['timestamp'].dt.hour

        hourly = dashboard_data.groupby('hour')['cpu_usage_percent'].mean()
        axes[1, 1].plot(hourly.index, hourly.values, color='tab:green', marker='o')
        axes[1, 1].set_title('Average CPU by Hour')
        axes[1, 1].set_xlabel('Hour of day')
        axes[1, 1].set_ylabel('%')
        axes[1, 1].grid(alpha=0.3)

        fig.tight_layout(rect=[0, 0, 1, 0.97])
        fig.savefig(output_path, dpi=200, bbox_inches='tight')
        plt.close(fig)

        logger.info('Saved dashboard to %s', output_path)
        return output_path

    def create_summary_report(
        self,
        df: pd.DataFrame,
        alert_count: int = 0,
        output_path: Optional[str] = None
    ) -> str:
        """Write a short summary explaining recent system health."""
        if df.empty:
            raise ValueError('No metrics available for report generation.')

        if output_path is None:
            output_path = os.path.join(self.output_dir, 'week4_summary.md')

        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        forecasts = ResourceForecaster(window=60, periods_ahead=6).forecast_resources(df)

        forecast_lines = []
        for metric, forecast in forecasts.items():
            next_value = forecast['predictions'][0]
            slope = forecast['slope_per_sample']
            if metric == 'cpu_usage_percent':
                forecast_lines.append(f'- CPU next estimate: {next_value:.1f}% (trend: {slope:+.2f} points/sample)')
            elif metric == 'memory_mb':
                forecast_lines.append(f'- Memory next estimate: {next_value:.0f} MB (trend: {slope:+.1f} MB/sample)')
            else:
                forecast_lines.append(f'- Processes next estimate: {next_value:.0f} (trend: {slope:+.1f}/sample)')

        forecast_text = '\n'.join(forecast_lines) or '- Not enough data for a forecast'
        summary = f"""# Week 4 System Health Summary

## Overview
- Start time: {start_time}
- End time: {end_time}
- Total samples: {len(df)}
- Alert count: {alert_count}

## Key metrics
- CPU average: {df['cpu_usage_percent'].mean():.1f}%
- CPU peak: {df['cpu_usage_percent'].max():.1f}%
- Memory average: {df['memory_mb'].mean():.1f} MB
- Memory peak: {df['memory_mb'].max():.1f} MB
- Process count average: {df['process_count'].mean():.1f}

## Short-term forecast
These are estimates for the next few samples. They extend the recent trend;
they are warnings, not guarantees.
{forecast_text}

## Interpretation
This summary tells you how the machine behaved during the selected time window.
If CPU is consistently high, the system may be under load. If memory is high,
resources may be under pressure. Process count can help identify background work.
"""

        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(summary)

        logger.info('Saved report to %s', output_path)
        return output_path


def main():
    """Create a dashboard and summary for recent metrics."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    generator = DashboardReportGenerator(db_path='data/metrics.db', output_dir='reports/')
    df = generator.load_recent_metrics(hours=24)

    if df.empty:
        print('No metrics found. Run the C monitor first to generate data.')
        return

    dashboard_path = generator.create_dashboard(df)
    report_path = generator.create_summary_report(df, alert_count=0)
    print(f'Dashboard created: {dashboard_path}')
    print(f'Report created: {report_path}')


if __name__ == '__main__':
    main()
