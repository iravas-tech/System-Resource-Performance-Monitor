"""
Pattern clustering module for identifying system behavior patterns.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class PatternClusterer:
    """Identify and cluster patterns in system metrics."""

    def __init__(self):
        """Initialize clusterer."""
        self.kmeans_models = {}
        self.dbscan_models = {}
        self.scalers = {}

    def cluster_temporal_patterns(
        self,
        df: pd.DataFrame,
        features: List[str],
        n_clusters: int = 3,
        window_size: int = 60
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Cluster system states based on temporal windows.

        Args:
            df: DataFrame with metrics
            features: Features to use for clustering
            n_clusters: Number of clusters
            window_size: Samples per window

        Returns:
            Tuple of (DataFrame with cluster labels, cluster centers)
        """
        df_copy = df.copy()
        X = df[features].values

        # Normalize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        df_copy['temporal_cluster'] = clusters

        self.kmeans_models['temporal'] = kmeans
        self.scalers['temporal'] = scaler

        logger.info(f"Clustered data into {n_clusters} temporal patterns")
        return df_copy, kmeans.cluster_centers_

    def cluster_by_hour(
        self,
        df: pd.DataFrame,
        features: List[str],
        n_clusters: int = 2
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Find usage patterns by hour of day.

        Args:
            df: DataFrame with metrics and 'hour' column
            features: Features to analyze
            n_clusters: Clusters per hour

        Returns:
            Tuple of (DataFrame with hour patterns, pattern summary dict)
        """
        df_copy = df.copy()

        if 'hour' not in df_copy.columns:
            logger.warning("'hour' column not found, cannot cluster by hour")
            return df_copy, {}

        patterns_by_hour = {}

        for hour in range(24):
            hour_data = df_copy[df_copy['hour'] == hour]

            if len(hour_data) == 0:
                continue

            X = hour_data[features].values
            if len(X) < n_clusters:
                n_clusters_hour = max(1, len(X) - 1)
            else:
                n_clusters_hour = n_clusters

            kmeans = KMeans(n_clusters=n_clusters_hour, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)

            patterns_by_hour[hour] = {
                'n_clusters': n_clusters_hour,
                'centers': kmeans.cluster_centers_,
                'inertia': kmeans.inertia_
            }

            # Assign hourly pattern labels
            hour_labels = np.full(len(df_copy), -1)
            hour_mask = df_copy['hour'] == hour
            hour_labels[hour_mask.values] = clusters

            df_copy[f'hour_{hour:02d}_pattern'] = hour_labels

        logger.info(f"Identified usage patterns for {len(patterns_by_hour)} hours")
        return df_copy, patterns_by_hour

    def cluster_cpu_memory_relationship(
        self,
        df: pd.DataFrame,
        n_clusters: int = 4
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Identify relationship patterns between CPU and memory usage.

        Args:
            df: DataFrame with cpu_usage_percent and memory_mb columns
            n_clusters: Number of clusters

        Returns:
            Tuple of (DataFrame with relationship clusters, summary)
        """
        df_copy = df.copy()

        features = ['cpu_usage_percent', 'memory_mb']
        X = df[features].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        df_copy['cpu_memory_pattern'] = clusters

        # Describe patterns
        patterns = {}
        for i in range(n_clusters):
            mask = clusters == i
            patterns[f'pattern_{i}'] = {
                'count': mask.sum(),
                'avg_cpu': df.loc[mask, 'cpu_usage_percent'].mean(),
                'avg_memory': df.loc[mask, 'memory_mb'].mean(),
                'avg_memory_available': df.loc[mask, 'memory_available_mb'].mean()
            }

        logger.info(f"Identified {n_clusters} CPU-memory relationship patterns")
        return df_copy, patterns

    def detect_anomalous_patterns(
        self,
        df: pd.DataFrame,
        features: List[str],
        eps: float = 0.5,
        min_samples: int = 5
    ) -> Tuple[pd.DataFrame, int]:
        """
        Detect anomalous patterns using DBSCAN.

        Args:
            df: DataFrame with metrics
            features: Features to analyze
            eps: DBSCAN epsilon parameter
            min_samples: DBSCAN min_samples parameter

        Returns:
            Tuple of (DataFrame with cluster labels, number of anomalies)
        """
        df_copy = df.copy()

        X = df[features].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        clusters = dbscan.fit_predict(X_scaled)

        df_copy['anomaly_pattern'] = clusters

        # Count anomalies (labeled as -1)
        n_anomalies = (clusters == -1).sum()
        n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)

        logger.info(f"DBSCAN identified {n_clusters} clusters and {n_anomalies} anomalies")
        return df_copy, n_anomalies

    def get_pattern_profiles(self, df: pd.DataFrame, pattern_col: str) -> dict:
        """
        Get statistical profiles of each pattern.

        Args:
            df: DataFrame with pattern labels
            pattern_col: Column name containing pattern labels

        Returns:
            Dictionary of pattern statistics
        """
        if pattern_col not in df.columns:
            logger.warning(f"Pattern column {pattern_col} not found")
            return {}

        profiles = {}

        for pattern_id in df[pattern_col].unique():
            if pattern_id == -1:
                continue

            mask = df[pattern_col] == pattern_id
            pattern_data = df[mask]

            profiles[f'pattern_{pattern_id}'] = {
                'count': mask.sum(),
                'cpu_mean': pattern_data['cpu_usage_percent'].mean(),
                'cpu_std': pattern_data['cpu_usage_percent'].std(),
                'memory_mean': pattern_data['memory_mb'].mean(),
                'memory_std': pattern_data['memory_mb'].std(),
                'process_count_mean': pattern_data['process_count'].mean()
            }

        return profiles
