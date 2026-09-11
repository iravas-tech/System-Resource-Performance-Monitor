"""
Weeks 3 and 4 - simple end-to-end pipeline.

This script connects the pieces:
1. look at recent system data
2. check for unusual behavior
3. generate a dashboard
4. create a short summary report

In plain English: it turns raw system data into something a person can read.
"""

import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from dashboard_report import DashboardReportGenerator
from real_time_alerts import RealTimeAlertEngine


logger = logging.getLogger(__name__)


class Week3_4_Orchestrator:
    """Run the full operational analytics pipeline."""

    def __init__(self, db_path: str = 'data/metrics.db'):
        self.db_path = db_path
        self.alert_engine = RealTimeAlertEngine(db_path=db_path)
        self.dashboard_generator = DashboardReportGenerator(db_path=db_path, output_dir='reports/')

    def run(self, hours: int = 24):
        """Execute the combined Week 3/4 pipeline."""
        print('\n' + '=' * 68)
        print('WEEK 3 & 4: LIVE ANALYSIS + DASHBOARD REPORTING')
        print('=' * 68)

        alerts = self.alert_engine.evaluate_recent_data(hours=hours)
        print(self.alert_engine.create_alert_summary(alerts))

        df = self.dashboard_generator.load_recent_metrics(hours=hours)
        if df.empty:
            print('No metrics were found, so no dashboard could be generated.')
            return False

        dashboard_path = self.dashboard_generator.create_dashboard(df)
        report_path = self.dashboard_generator.create_summary_report(df, alert_count=len(alerts))

        print('\nGenerated outputs:')
        print(f'  - Dashboard: {dashboard_path}')
        print(f'  - Report:    {report_path}')
        print('\n✅ Week 3 and Week 4 pipeline complete.')
        return True


def main():
    """Entry point for the Week 3/4 pipeline."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    orchestrator = Week3_4_Orchestrator(db_path='data/metrics.db')
    orchestrator.run(hours=24)


if __name__ == '__main__':
    main()
