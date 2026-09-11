"""
Print the SQLite database in a beginner-readable format.

The .db file itself is not meant to be opened like a text file.
This script asks SQLite to show the tables, row counts, and latest readings.
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def format_timestamp(value):
    """Turn a Unix timestamp into a normal date and time."""
    if value is None:
        return 'none'
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')


def inspect_database(database_path: str, limit: int = 10) -> None:
    """Print a simple summary of the collected data."""
    path = Path(database_path)
    if not path.exists():
        print(f'Database not found: {path}')
        print('Start the monitor first so it can create data/metrics.db.')
        return

    connection = sqlite3.connect(path)
    try:
        print(f'Database: {path}')
        print()
        print('What the tables mean:')
        print('- system_metrics: one computer-wide reading every few seconds')
        print('- process_metrics: readings for individual programs, when enabled')
        print()

        for table in ('system_metrics', 'process_metrics'):
            count = connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            print(f'{table}: {count} rows')

        print('\nLatest system readings:')
        rows = connection.execute(
            """
            SELECT timestamp, cpu_usage_percent, memory_mb, process_count
            FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        if not rows:
            print('No system readings have been collected yet.')
            return

        print('time                  cpu %   memory MB   processes')
        print('-' * 58)
        for timestamp, cpu, memory, processes in reversed(rows):
            print(
                f'{format_timestamp(timestamp):19} '
                f'{cpu:6.1f}   {memory:10}   {processes:9}'
            )
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read metrics.db in plain English.')
    parser.add_argument('--database', default='data/metrics.db')
    parser.add_argument('--limit', type=int, default=10)
    arguments = parser.parse_args()
    inspect_database(arguments.database, arguments.limit)
