"""
Example Python script for data analysis.
This demonstrates how to use the analysis modules.
"""

import sys
import logging
from datetime import datetime, timedelta
from data_loader import MetricsDataLoader
from preprocessing import MetricsPreprocessor
from models.anomaly_detection import AnomalyDetector
from models.pattern_clustering import PatternClusterer
from models.trend_analysis import TrendAnalyzer
from visualization import (
    plot_system_metrics,
    plot_cpu_memory_scatter,
    plot_anomalies,
    plot_cpu_spikes
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_metrics(db_path='../data/metrics.db', hours=24):
    """
    Main analysis function.
    """
    logger.info("=" * 60)
    logger.info("System Metrics Analysis")
    logger.info("=" * 60)

    # Load data
    logger.info("Loading metrics from database...")
    loader = MetricsDataLoader(db_path)
    if not loader.connect():
        logger.error("Failed to connect to database")
        return

    try:
        # Get database statistics
        stats = loader.get_database_stats()
        logger.info(f"Database stats: {stats}")

        # Load recent data
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        df = loader.load_system_metrics(start_time, end_time)

        if df.empty:
            logger.warning(f"No data found in the last {hours} hours")
            return

        logger.info(f"Loaded {len(df)} metrics from {start_time} to {end_time}")

        # Preprocessing
        logger.info("Preprocessing data...")
        preprocessor = MetricsPreprocessor()
        df_clean = preprocessor.prepare_for_ml(
            df,
            remove_outliers=True,
            normalize=True,
            add_time_features=True,
            add_rolling_features=False
        )

        logger.info("Feature statistics:")
        logger.info(preprocessor.get_feature_statistics(df))

        # Anomaly Detection
        logger.info("\n" + "=" * 60)
        logger.info("Anomaly Detection")
        logger.info("=" * 60)

        detector = AnomalyDetector(contamination=0.05)
        features = ['cpu_usage_percent', 'memory_mb', 'process_count']

        # Isolation Forest
        df_if, anomalies_if = detector.detect_isolation_forest(df_clean, features)
        logger.info(f"Isolation Forest: {anomalies_if.sum()} anomalies detected")

        # CPU spike detection
        df_spikes, spikes = detector.detect_cpu_spike(df_clean, threshold_percent=80.0)
        logger.info(f"CPU Spike Detection: {spikes.sum()} spike periods detected")

        # Pattern Clustering
        logger.info("\n" + "=" * 60)
        logger.info("Pattern Clustering")
        logger.info("=" * 60)

        clusterer = PatternClusterer()

        # Temporal patterns
        df_clusters, centers = clusterer.cluster_temporal_patterns(
            df_clean,
            features,
            n_clusters=3
        )
        logger.info("Temporal patterns identified")

        # Hourly patterns
        if 'hour' in df_clean.columns:
            df_hourly, hourly_patterns = clusterer.cluster_by_hour(
                df_clean,
                features,
                n_clusters=2
            )
            logger.info(f"Hourly patterns: {len(hourly_patterns)} hours analyzed")

        # CPU-Memory relationship
        df_rel, rel_patterns = clusterer.cluster_cpu_memory_relationship(df_clean, n_clusters=4)
        logger.info("CPU-Memory relationship patterns:")
        for pattern_name, pattern_info in rel_patterns.items():
            logger.info(f"  {pattern_name}: CPU={pattern_info['avg_cpu']:.1f}%, "
                       f"Memory={pattern_info['avg_memory']:.0f}MB")

        # Trend Analysis
        logger.info("\n" + "=" * 60)
        logger.info("Trend Analysis")
        logger.info("=" * 60)

        analyzer = TrendAnalyzer()

        # Calculate trends
        df_trends = analyzer.calculate_trend(df_clean, 'cpu_usage_percent', window=10)
        df_trends, trend_info = analyzer.linear_regression_trend(
            df_trends,
            'cpu_usage_percent',
            window=100
        )
        if trend_info:
            logger.info(f"CPU Trend: slope={trend_info['slope']:.6f}, "
                       f"R²={trend_info['r_squared']:.4f}")

        # Detect trend changes
        df_changes, changes = analyzer.detect_trend_change(
            df_clean,
            'cpu_usage_percent',
            window1=10,
            window2=20,
            threshold=0.05
        )
        logger.info(f"Trend changes detected: {changes.sum()}")

        # Seasonality
        df_season, seasonal_factors = analyzer.calculate_seasonality(
            df_clean,
            'cpu_usage_percent',
            period=24
        )
        if len(seasonal_factors) > 0:
            logger.info(f"Seasonality factors (hourly): min={seasonal_factors.min():.2f}, "
                       f"max={seasonal_factors.max():.2f}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Analysis Summary")
        logger.info("=" * 60)
        logger.info(f"Total records analyzed: {len(df)}")
        logger.info(f"Anomalies detected (IF): {anomalies_if.sum()}")
        logger.info(f"CPU spikes detected: {spikes.sum()}")
        logger.info(f"Temporal clusters: 3")
        logger.info(f"Hourly patterns: 24 hours")

        # Example visualization (commented by default)
        # logger.info("\nGenerating visualizations...")
        # plot_system_metrics(df, save_path='system_metrics.png')
        # plot_cpu_memory_scatter(df, save_path='cpu_memory_scatter.png')
        # plot_anomalies(df_if, 'cpu_usage_percent', 'anomaly_if', 'anomalies.png')
        # plot_cpu_spikes(df_spikes, save_path='cpu_spikes.png')

        logger.info("Analysis complete!")

    finally:
        loader.disconnect()


if __name__ == '__main__':
    # Run analysis on last 24 hours of data
    analyze_metrics(hours=24)
