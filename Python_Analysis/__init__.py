"""
Module initialization file for Python_Analysis package.
"""

__version__ = "0.1.0"
__author__ = "System Resource Monitor Team"

# Import main analysis components
try:
    from .data_loader import MetricsDataLoader, load_metrics_dataframe
    from .preprocessing import MetricsPreprocessor
    from .models.anomaly_detection import AnomalyDetector
    from .models.pattern_clustering import PatternClusterer
    from .models.trend_analysis import TrendAnalyzer
    from .visualization import (
        plot_system_metrics,
        plot_cpu_memory_scatter,
        plot_anomalies,
        plot_hourly_patterns,
        plot_cluster_analysis,
        plot_cpu_spikes
    )
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")

__all__ = [
    'MetricsDataLoader',
    'MetricsPreprocessor',
    'AnomalyDetector',
    'PatternClusterer',
    'TrendAnalyzer',
    'load_metrics_dataframe',
    'plot_system_metrics',
    'plot_cpu_memory_scatter',
    'plot_anomalies',
    'plot_hourly_patterns',
    'plot_cluster_analysis',
    'plot_cpu_spikes'
]
