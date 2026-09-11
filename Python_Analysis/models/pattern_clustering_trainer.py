"""
Week 2 - Python Analysis: Pattern Clustering Model Training

WEEK 2 ENHANCEMENT:
This module trains pattern clustering models to find and group similar
system behavior patterns.

What is Pattern Clustering?
Clustering groups similar things together. Think of it like:
- Sorting laundry: Group similar colors, similar sizes
- Your work schedule: "8-10 AM = High CPU", "12-1 PM = Low CPU"
- These are behavioral "clusters" or patterns

Algorithms Used:
1. K-Means: Divides data into K groups (you specify number)
2. DBSCAN: Finds groups by density (doesn't need K)
3. Temporal Clustering: Groups similar time periods

Practical Applications:
- Find "normal" work hour patterns
- Find unusual time-based anomalies
- Identify periodic trends (every Monday is busy, etc.)

Training Process:
1. Load 30 days of data
2. Extract temporal features (hour of day, day of week, etc.)
3. Add system metrics (CPU, memory, disk)
4. Train clustering models
5. Analyze and interpret clusters
6. Save cluster definitions
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
import joblib
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import project modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from data_loader import MetricsDataLoader
from preprocessing import MetricsPreprocessor


class PatternClusteringTrainer:
    """
    Trains clustering models to identify usage patterns in system metrics.
    
    Analogy: Like a retail manager analyzing customer shopping patterns
    - Morning: Specific types of customers shop
    - Afternoon: Different customer patterns
    - Evening: Yet another pattern
    - Train on many weeks to identify recurring patterns
    - Then can predict what to expect at each time
    """
    
    def __init__(self, database_path='data/metrics.db'):
        """Initialize clustering trainer"""
        self.db_path = database_path
        self.loader = MetricsDataLoader(database_path)
        self.preprocessor = MetricsPreprocessor()
        
        # Models
        self.kmeans_model = None
        self.dbscan_model = None
        self.scaler = None
        
        # Cluster analysis
        self.cluster_profiles = {}
        self.cluster_metrics = {}
        
    def load_and_prepare_data(self, days=30):
        """
        Load data and engineer temporal/pattern features.
        
        Features created:
        - Hour of day (0-23): What hour of day?
        - Day of week (0-6): Monday-Sunday
        - Time category: Work hours? Off hours?
        - Rolling averages: CPU/memory trends
        - Periodic features: Sin/cos of time (captures circularity)
        
        Returns:
            Tuple: (feature_array, dataframe_with_features)
        """
        print(f"[Clustering] Loading {days} days of data...")
        
        try:
            # Load data
            self.loader.connect()
            df = self.loader.load_system_metrics()
            
            if df is None or len(df) == 0:
                print("[Clustering] ERROR: No data found!")
                return None, None
            
            # Filter to requested days
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                cutoff_date = datetime.now() - timedelta(days=days)
                df = df[df['timestamp'] >= cutoff_date]
            else:
                # If no timestamp, add one (sequential)
                df['timestamp'] = pd.to_datetime(range(len(df)), unit='s', origin='2026-01-01')
            
            print(f"[Clustering] Loaded {len(df)} data points")
            
            # Engineer temporal features
            df = self._engineer_features(df)
            
            # Select features for clustering
            feature_columns = [
                # Temporal features (when it happened)
                'hour_of_day',
                'day_of_week',
                'hour_sin',  # Circular hour encoding
                'hour_cos',
                
                # System metrics
                'cpu_usage_percent',
                'memory_mb',
                'disk_read_bytes',
                'disk_write_bytes',
                'network_bytes_sent',
                'network_bytes_recv',
                'process_count',
                
                # Trend features (is it going up/down?)
                'cpu_rolling_mean',
                'memory_rolling_mean'
            ]
            
            # Keep only existing features
            available_features = [col for col in feature_columns if col in df.columns]
            
            X = df[available_features].copy()
            
            # Handle missing values
            X = X.ffill().bfill().fillna(0)
            X = X.replace([np.inf, -np.inf], 0)
            
            print(f"[Clustering] Features prepared: {len(available_features)} features")
            print(f"[Clustering] Data shape: {X.shape}")
            
            return X, df
            
        except Exception as e:
            print(f"[Clustering] ERROR: {e}")
            return None, None
        finally:
            self.loader.disconnect()
    
    def _engineer_features(self, df):
        """
        Create additional features from timestamps.
        
        Purpose: These features help clustering understand patterns
        that repeat at specific times.
        
        Features created:
        - hour_of_day: 0-23 (what hour?)
        - day_of_week: 0-6 (what day?)
        - hour_sin/hour_cos: Circular encoding of hour
        - Rolling means: Smoothed trends
        """
        print("[Clustering] Engineering temporal features...")
        
        # Extract time components
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Create circular encoding of hour
        # Why? Hour 0 is close to hour 23 (just wrapped around)
        # Sin/cos captures this circularity
        df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
        
        # Create time category
        df['is_work_hours'] = ((df['hour_of_day'] >= 8) & 
                               (df['hour_of_day'] < 18)).astype(int)
        
        # Rolling averages (smoothed trends)
        # Look at 1-hour window (12 measurements at 5-second intervals)
        if 'cpu_usage_percent' in df.columns:
            df['cpu_rolling_mean'] = df['cpu_usage_percent'].rolling(
                window=12, min_periods=1
            ).mean()
        
        if 'memory_mb' in df.columns:
            df['memory_rolling_mean'] = df['memory_mb'].rolling(
                window=12, min_periods=1
            ).mean()
        
        return df
    
    def train_kmeans(self, X, n_clusters_range=(3, 10)):
        """
        Train K-Means clustering model.
        
        K-Means intuition:
        - K = number of clusters (patterns) to find
        - Algorithm: Assign each point to nearest cluster center
        - Iteratively adjust cluster centers until stable
        - Think: Grouping cities into regions
        
        Parameters:
            X: Feature data
            n_clusters_range: Range of K values to test
        
        Returns:
            Best model and analysis
        """
        print(f"[Clustering] Training K-Means...")
        
        best_score = -np.inf
        best_model = None
        best_k = None
        
        # Test different cluster numbers
        for k in range(n_clusters_range[0], n_clusters_range[1] + 1):
            print(f"[Clustering]   Testing K={k}...", end='')
            
            model = KMeans(
                n_clusters=k,
                random_state=42,
                n_init=10,  # Try 10 different initializations
                max_iter=300
            )
            model.fit(X)
            
            # Evaluate with silhouette score
            # Range: -1 to 1 (higher is better)
            # Measures how similar point is to its cluster
            score = silhouette_score(X, model.labels_)
            print(f" Score: {score:.3f}")
            
            if score > best_score:
                best_score = score
                best_model = model
                best_k = k
        
        print(f"[Clustering] K-Means best K: {best_k} (score: {best_score:.3f})")
        
        # Analyze clusters
        self._analyze_kmeans_clusters(best_model, X)
        
        return best_model
    
    def train_dbscan(self, X, eps=0.5, min_samples=5):
        """
        Train DBSCAN clustering model.
        
        DBSCAN intuition:
        - Finds clusters based on density (not needing to specify K)
        - Points close together = same cluster
        - Points far apart = different clusters
        - Can find clusters of any shape (not just spheres like K-Means)
        
        Parameters:
            X: Feature data
            eps: Distance threshold for neighbors
            min_samples: Minimum points to form a cluster
        
        Returns:
            Trained model
        """
        print(f"[Clustering] Training DBSCAN...")
        
        model = DBSCAN(
            eps=eps,
            min_samples=min_samples
        )
        model.fit(X)
        
        # Count clusters and noise points
        labels = model.labels_
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        print(f"[Clustering] DBSCAN found {n_clusters} clusters")
        print(f"[Clustering]   - Noise points: {n_noise}")
        print(f"[Clustering]   - Points in clusters: {len(labels) - n_noise}")
        
        # Calculate Davies-Bouldin Index (lower is better)
        if n_clusters > 1:
            db_index = davies_bouldin_score(X, labels)
            print(f"[Clustering]   - Davies-Bouldin Index: {db_index:.3f}")
        
        return model
    
    def _analyze_kmeans_clusters(self, model, X):
        """
        Analyze K-Means cluster characteristics.
        
        Shows what each cluster represents:
        - Average CPU at each cluster
        - Average memory at each cluster
        - What time of day is this cluster
        - Size of cluster
        """
        print(f"\n[Clustering] Cluster Analysis (K-Means):")
        print("-" * 60)
        
        labels = model.labels_
        n_clusters = model.n_clusters
        
        for cluster_id in range(n_clusters):
            # Get points in this cluster
            cluster_mask = labels == cluster_id
            cluster_points = X.loc[cluster_mask]
            
            print(f"\nCluster {cluster_id}:")
            print(f"  - Size: {np.sum(cluster_mask)} points ({100*np.sum(cluster_mask)/len(X):.1f}%)")
            
            # Show average values
            if 'hour_of_day' in X.columns:
                avg_hour = cluster_points['hour_of_day'].mean()
                print(f"  - Avg time: {int(avg_hour):02d}:00 (hour {int(avg_hour)})")
            
            if 'cpu_usage_percent' in X.columns:
                avg_cpu = cluster_points['cpu_usage_percent'].mean()
                print(f"  - Avg CPU: {avg_cpu:.1f}%")
            
            if 'memory_mb' in X.columns:
                avg_mem = cluster_points['memory_mb'].mean()
                print(f"  - Avg Memory: {avg_mem:.1f} MB")
    
    def save_models(self, output_dir='models/'):
        """Save trained clustering models and cluster definitions"""
        print(f"\n[Clustering] Saving models to {output_dir}...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save models
        if self.kmeans_model:
            joblib.dump(self.kmeans_model, os.path.join(output_dir, 'kmeans_patterns.pkl'))
            print("[Clustering] Saved K-Means model")
        
        if self.dbscan_model:
            joblib.dump(self.dbscan_model, os.path.join(output_dir, 'dbscan_patterns.pkl'))
            print("[Clustering] Saved DBSCAN model")
        
        if self.scaler:
            joblib.dump(self.scaler, os.path.join(output_dir, 'clustering_scaler.pkl'))
            print("[Clustering] Saved feature scaler")
        
        # Save cluster metadata
        with open(os.path.join(output_dir, 'clustering_metadata.txt'), 'w') as f:
            f.write(f"Training Date: {datetime.now()}\n")
            f.write(f"Models: K-Means, DBSCAN\n")
            f.write(f"Clusters Found: {self.cluster_metrics}\n")
    
    def train_full_pipeline(self, days=30):
        """
        Complete training pipeline for pattern clustering.
        
        Steps:
        1. Load and prepare data with temporal features
        2. Scale features
        3. Train K-Means
        4. Train DBSCAN
        5. Compare and save models
        
        Parameters:
            days: Historical data to use (default: 30)
        """
        print("\n" + "="*60)
        print("PATTERN CLUSTERING - TRAINING PIPELINE")
        print("="*60)
        
        # Step 1: Load data
        X, df = self.load_and_prepare_data(days=days)
        if X is None:
            return False
        
        # Step 2: Scale features
        print("[Clustering] Scaling features...")
        self.scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )
        
        # Step 3: Train K-Means
        print("\n[Clustering] Training K-Means clustering...")
        self.kmeans_model = self.train_kmeans(X_scaled, n_clusters_range=(3, 8))
        
        # Step 4: Train DBSCAN
        print("\n[Clustering] Training DBSCAN clustering...")
        self.dbscan_model = self.train_dbscan(X_scaled, eps=1.5, min_samples=10)
        
        # Step 5: Save
        print("\n[Clustering] Saving trained models...")
        self.save_models()
        
        print("\n" + "="*60)
        print("PATTERN CLUSTERING TRAINING COMPLETE!")
        print("="*60)
        return True


def main():
    """
    Main execution: Run the pattern clustering training pipeline.
    
    This identifies temporal and behavioral patterns in your metrics,
    learning what "normal" looks like at different times.
    """
    print("\n" + "="*60)
    print("WEEK 2: PATTERN CLUSTERING MODEL TRAINING")
    print("="*60)
    print()
    print("This script identifies patterns in your system behavior")
    print("over 30 days of collected metrics.")
    print()
    print("Models trained:")
    print("  1. K-Means - Groups data into K behavioral clusters")
    print("  2. DBSCAN - Density-based clustering (auto-finds clusters)")
    print()
    print("Pattern Features:")
    print("  - Temporal: Time of day, day of week")
    print("  - Behavioral: CPU, memory, disk usage")
    print("  - Trends: Rolling averages and changes")
    print()
    print("Output: Trained models saved to models/")
    print("="*60 + "\n")
    
    # Create trainer
    trainer = PatternClusteringTrainer()
    
    # Run pipeline
    success = trainer.train_full_pipeline(days=30)
    
    if success:
        print("\n✅ Pattern clustering training successful!")
        print("Patterns learned and ready for use.")
    else:
        print("\n❌ Training failed!")
        print("Check database and data availability.")


if __name__ == '__main__':
    main()
