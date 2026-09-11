"""
Data loader module for reading metrics from SQLite database.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MetricsDataLoader:
    """Load and manage system metrics from SQLite database."""

    def __init__(self, db_path: str):
        """
        Initialize data loader.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None

    def connect(self) -> bool:
        """Connect to database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")

    def load_system_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load system metrics within time range.

        Args:
            start_time: Start time (defaults to 24 hours ago)
            end_time: End time (defaults to now)

        Returns:
            DataFrame with columns: timestamp, cpu_usage_percent, memory_mb, etc.
        """
        if not self.connection:
            logger.warning("Database not connected, connecting now...")
            if not self.connect():
                return pd.DataFrame()

        # Set default time range (last 24 hours)
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        query = """
        SELECT 
            timestamp,
            cpu_usage_percent,
            memory_mb,
            memory_available_mb,
            disk_read_bytes,
            disk_write_bytes,
            network_bytes_sent,
            network_bytes_recv,
            process_count,
            cpu_temp_celsius
        FROM system_metrics
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """

        try:
            df = pd.read_sql_query(
                query,
                self.connection,
                params=(start_ts, end_ts)
            )

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

            logger.info(f"Loaded {len(df)} system metrics from {start_time} to {end_time}")
            return df

        except sqlite3.Error as e:
            logger.error(f"Failed to load system metrics: {e}")
            return pd.DataFrame()

    def load_process_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load process metrics within time range.

        Args:
            start_time: Start time
            end_time: End time
            top_n: Limit to top N processes by memory usage

        Returns:
            DataFrame with process metrics
        """
        if not self.connection:
            logger.warning("Database not connected, connecting now...")
            if not self.connect():
                return pd.DataFrame()

        # Set default time range
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        query = """
        SELECT 
            timestamp,
            process_id,
            process_name,
            cpu_usage_percent,
            memory_mb,
            disk_io_bytes,
            network_bytes
        FROM process_metrics
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC, memory_mb DESC
        """

        try:
            df = pd.read_sql_query(
                query,
                self.connection,
                params=(start_ts, end_ts)
            )

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

            # Filter to top N processes if specified
            if top_n:
                top_pids = df.groupby('process_id')['memory_mb'].max().nlargest(top_n).index
                df = df[df['process_id'].isin(top_pids)]

            logger.info(f"Loaded {len(df)} process metrics")
            return df

        except sqlite3.Error as e:
            logger.error(f"Failed to load process metrics: {e}")
            return pd.DataFrame()

    def get_database_stats(self) -> dict:
        """Get statistics about database contents."""
        if not self.connection:
            return {}

        stats = {}

        try:
            # Count records
            cursor = self.connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM system_metrics")
            stats['system_metrics_count'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM process_metrics")
            stats['process_metrics_count'] = cursor.fetchone()[0]

            # Get time range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM system_metrics")
            result = cursor.fetchone()
            if result[0]:
                stats['start_time'] = datetime.fromtimestamp(result[0])
                stats['end_time'] = datetime.fromtimestamp(result[1])

            logger.info(f"Database stats: {stats}")
            return stats

        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


def load_metrics_dataframe(
    db_path: str,
    hours: int = 24
) -> pd.DataFrame:
    """
    Convenience function to load recent metrics.

    Args:
        db_path: Path to SQLite database
        hours: Number of hours of data to load

    Returns:
        DataFrame with metrics
    """
    loader = MetricsDataLoader(db_path)
    loader.connect()

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    df = loader.load_system_metrics(start_time, end_time)
    loader.disconnect()

    return df
