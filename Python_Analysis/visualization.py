"""
Visualization module for system metrics and analysis results.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (15, 8)


def plot_system_metrics(
    df: pd.DataFrame,
    save_path: Optional[str] = None
) -> None:
    """
    Plot system metrics over time.

    Args:
        df: DataFrame with system metrics
        save_path: Path to save figure
    """
    if 'timestamp' not in df.columns:
        logger.error("'timestamp' column required")
        return

    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

    # CPU usage
    axes[0].plot(df['timestamp'], df['cpu_usage_percent'], label='CPU Usage', linewidth=2)
    axes[0].set_ylabel('CPU Usage (%)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Memory usage
    axes[1].plot(df['timestamp'], df['memory_mb'], label='Memory Used', color='orange', linewidth=2)
    axes[1].plot(df['timestamp'], df['memory_available_mb'], label='Memory Available', 
                color='green', alpha=0.7, linewidth=2)
    axes[1].set_ylabel('Memory (MB)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Process count
    axes[2].plot(df['timestamp'], df['process_count'], label='Process Count', 
                color='red', linewidth=2)
    axes[2].set_ylabel('Process Count')
    axes[2].set_xlabel('Time')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved system metrics plot to {save_path}")
    else:
        plt.show()

    plt.close()


def plot_cpu_memory_scatter(
    df: pd.DataFrame,
    save_path: Optional[str] = None
) -> None:
    """
    Plot CPU vs Memory usage scatter plot.

    Args:
        df: DataFrame with metrics
        save_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    scatter = ax.scatter(df['cpu_usage_percent'], df['memory_mb'],
                        c=df.index, cmap='viridis', s=30, alpha=0.6)

    ax.set_xlabel('CPU Usage (%)', fontsize=12)
    ax.set_ylabel('Memory Used (MB)', fontsize=12)
    ax.set_title('CPU vs Memory Usage Relationship', fontsize=14, fontweight='bold')

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Sample Index', fontsize=10)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved scatter plot to {save_path}")
    else:
        plt.show()

    plt.close()


def plot_anomalies(
    df: pd.DataFrame,
    metric_col: str,
    anomaly_col: str,
    save_path: Optional[str] = None
) -> None:
    """
    Plot metrics with anomalies highlighted.

    Args:
        df: DataFrame with metrics and anomaly flags
        metric_col: Metric column to plot
        anomaly_col: Anomaly flag column
        save_path: Path to save figure
    """
    if 'timestamp' not in df.columns:
        logger.error("'timestamp' column required")
        return

    fig, ax = plt.subplots(figsize=(15, 6))

    # Plot metric
    ax.plot(df['timestamp'], df[metric_col], label=metric_col, linewidth=2)

    # Highlight anomalies
    anomalies = df[df[anomaly_col] == 1]
    if len(anomalies) > 0:
        ax.scatter(anomalies['timestamp'], anomalies[metric_col], 
                  color='red', s=100, label='Anomalies', zorder=5, marker='x')

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel(metric_col, fontsize=12)
    ax.set_title(f'{metric_col} with Detected Anomalies', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved anomaly plot to {save_path}")
    else:
        plt.show()

    plt.close()


def plot_hourly_patterns(
    df: pd.DataFrame,
    metric_col: str,
    save_path: Optional[str] = None
) -> None:
    """
    Plot average metrics by hour of day.

    Args:
        df: DataFrame with metrics and 'hour' column
        metric_col: Metric to analyze
        save_path: Path to save figure
    """
    if 'hour' not in df.columns:
        logger.error("'hour' column required")
        return

    hourly_avg = df.groupby('hour')[metric_col].agg(['mean', 'std'])

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(hourly_avg.index, hourly_avg['mean'], marker='o', linewidth=2, markersize=8)
    ax.fill_between(hourly_avg.index,
                    hourly_avg['mean'] - hourly_avg['std'],
                    hourly_avg['mean'] + hourly_avg['std'],
                    alpha=0.3)

    ax.set_xlabel('Hour of Day', fontsize=12)
    ax.set_ylabel(metric_col, fontsize=12)
    ax.set_title(f'Daily Pattern: {metric_col} by Hour', fontsize=14, fontweight='bold')
    ax.set_xticks(range(24))
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved hourly pattern plot to {save_path}")
    else:
        plt.show()

    plt.close()


def plot_cluster_analysis(
    df: pd.DataFrame,
    cluster_col: str,
    feature1: str,
    feature2: str,
    save_path: Optional[str] = None
) -> None:
    """
    Plot clusters in 2D space.

    Args:
        df: DataFrame with metrics and cluster labels
        cluster_col: Column with cluster assignments
        feature1: First feature to plot
        feature2: Second feature to plot
        save_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    scatter = ax.scatter(df[feature1], df[feature2], c=df[cluster_col],
                        cmap='tab10', s=50, alpha=0.6)

    ax.set_xlabel(feature1, fontsize=12)
    ax.set_ylabel(feature2, fontsize=12)
    ax.set_title(f'Cluster Analysis: {feature1} vs {feature2}', fontsize=14, fontweight='bold')

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Cluster', fontsize=10)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved cluster plot to {save_path}")
    else:
        plt.show()

    plt.close()


def plot_cpu_spikes(
    df: pd.DataFrame,
    save_path: Optional[str] = None
) -> None:
    """
    Plot CPU usage with spike detection.

    Args:
        df: DataFrame with cpu_usage_percent and cpu_spike columns
        save_path: Path to save figure
    """
    if 'timestamp' not in df.columns or 'cpu_spike' not in df.columns:
        logger.error("'timestamp' and 'cpu_spike' columns required")
        return

    fig, ax = plt.subplots(figsize=(15, 6))

    # Plot CPU usage
    ax.plot(df['timestamp'], df['cpu_usage_percent'], label='CPU Usage', linewidth=2)

    # Highlight spikes
    spikes = df[df['cpu_spike'] == 1]
    if len(spikes) > 0:
        ax.scatter(spikes['timestamp'], spikes['cpu_usage_percent'],
                  color='red', s=50, label='CPU Spikes', zorder=5, marker='^')

    ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Spike Threshold (80%)')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Usage (%)', fontsize=12)
    ax.set_title('CPU Usage with Spike Detection', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved CPU spike plot to {save_path}")
    else:
        plt.show()

    plt.close()
