"""
Week 2 - Python Analysis: Anomaly Detection Model Training

WEEK 2 ENHANCEMENT:
This module trains and validates anomaly detection models using the
collected system metrics from Week 1.

What is Anomaly Detection?
Anomaly detection finds unusual patterns in data. Think of it like:
- Normal heartbeat: 60-100 bpm (beats per minute)
- Anomaly: 180 bpm while resting → Something's wrong!

Algorithms Used:
1. Isolation Forest: Finds "outlier" data points
2. Local Outlier Factor (LOF): Finds points that are "locally rare"
3. Autoencoders: Neural network that learns normal patterns

How Training Works:
1. Load historical data (30 days)
2. Prepare/clean the data
3. Train model on normal data
4. Validate on test set
5. Save trained model for future use

When does this run?
- Periodically (weekly) to retrain with new data
- Or on-demand to detect anomalies in fresh data
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score
import joblib
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import our project modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from data_loader import MetricsDataLoader
from preprocessing import MetricsPreprocessor


class AnomalyDetectionTrainer:
    """
    Trains anomaly detection models on system metrics data.
    
    Analogy: Like training a doctor to recognize diseases
    - Healthy data = normal patients
    - Train on many healthy patients
    - Doctor learns what "normal" looks like
    - Then can detect "sick" patients
    """
    
    def __init__(self, database_path='data/metrics.db'):
        """Initialize trainer with database connection"""
        self.db_path = database_path
        self.loader = MetricsDataLoader(database_path)
        self.preprocessor = MetricsPreprocessor()
        
        # Model storage
        self.isolation_forest = None
        self.lof_model = None
        self.scaler = None
        
        # Performance metrics
        self.training_metrics = {}
        
    def load_data(self, days=30):
        """
        Load historical data from database.
        
        Parameters:
            days: How many days of historical data to load
                  Default: 30 (one month)
        
        Returns:
            DataFrame with cleaned metrics
        """
        print(f"[AnomalyDetection] Loading {days} days of data...")
        
        try:
            # Connect to database
            self.loader.connect()
            
            # Load system metrics
            df = self.loader.load_system_metrics()
            
            if df is None or len(df) == 0:
                print("[AnomalyDetection] ERROR: No data found in database!")
                return None
            
            # Filter to requested days
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                cutoff_date = datetime.now() - timedelta(days=days)
                df = df[df['timestamp'] >= cutoff_date]
            
            print(f"[AnomalyDetection] Loaded {len(df)} data points")
            return df
            
        except Exception as e:
            print(f"[AnomalyDetection] ERROR loading data: {e}")
            return None
        finally:
            self.loader.disconnect()
    
    def prepare_features(self, df):
        """
        Prepare features for model training.
        
        Steps:
        1. Select relevant columns (CPU, memory, disk, network)
        2. Handle missing values
        3. Normalize values (scale to 0-1 range)
        4. Create additional features (rates of change, etc.)
        
        Returns:
            Tuple: (feature_array, feature_names, scaler)
        """
        print("[AnomalyDetection] Preparing features...")
        
        # Select features to use for anomaly detection
        feature_columns = [
            'cpu_usage_percent',
            'memory_mb',
            'memory_available_mb',
            'disk_read_bytes',
            'disk_write_bytes',
            'network_bytes_sent',
            'network_bytes_recv',
            'process_count'
        ]
        
        # Filter to only columns that exist in our data
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) == 0:
            print("[AnomalyDetection] ERROR: No features found!")
            return None, None, None
        
        print(f"[AnomalyDetection] Using {len(available_features)} features: {available_features}")
        
        # Extract feature data
        X = df[available_features].copy()
        
        # Handle missing values
        # Strategy: Forward fill (use previous value) then backward fill
        X = X.ffill().bfill().fillna(0)
        
        # Handle infinite values
        X = X.replace([np.inf, -np.inf], 0)
        
        # Normalize/scale features
        # Why scale? Some features are 0-100 (CPU %), others are huge (bytes)
        # Scaling puts them all on same scale so model treats them fairly
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        print(f"[AnomalyDetection] Features prepared: shape {X_scaled.shape}")
        return X_scaled, available_features, self.scaler
    
    def train_isolation_forest(self, X_train, contamination=0.05):
        """
        Train Isolation Forest model.
        
        Isolation Forest intuition:
        - Normal points need many "splits" to isolate
        - Anomalous points can be isolated with few splits
        - Think: Separating one strange person from a crowd is easy!
        
        Parameters:
            X_train: Training data (samples × features)
            contamination: Expected percentage of anomalies (0.05 = 5%)
        
        Returns:
            Trained model
        """
        print("[AnomalyDetection] Training Isolation Forest...")
        
        # Create and train model
        model = IsolationForest(
            contamination=contamination,  # Expect ~5% anomalies
            random_state=42,              # For reproducibility
            n_estimators=100,             # Number of trees in forest
            max_samples='auto'            # Auto sample size
        )
        
        model.fit(X_train)
        
        # Predict anomalies on training set
        predictions = model.predict(X_train)
        # Note: predictions are -1 (anomaly) or 1 (normal)
        
        # Calculate metrics
        n_anomalies = np.sum(predictions == -1)
        print(f"[AnomalyDetection] Isolation Forest trained")
        print(f"[AnomalyDetection]   - Anomalies detected: {n_anomalies}/{len(predictions)}")
        print(f"[AnomalyDetection]   - Percentage: {100*n_anomalies/len(predictions):.2f}%")
        
        return model
    
    def train_lof(self, X_train, n_neighbors=20, contamination=0.05):
        """
        Train Local Outlier Factor model.
        
        Local Outlier Factor (LOF) intuition:
        - Looks at local neighborhood density
        - Points with lower local density = outliers
        - Think: Finding someone with unusual neighbors
        
        Parameters:
            X_train: Training data
            n_neighbors: How many neighbors to consider for density
            contamination: Expected anomaly percentage
        
        Returns:
            Trained model
        """
        print("[AnomalyDetection] Training Local Outlier Factor...")
        
        model = LocalOutlierFactor(
            n_neighbors=n_neighbors,      # Look at 20 nearest neighbors
            contamination=contamination,   # Expect ~5% anomalies
            novelty=True                  # Can detect anomalies in new data
        )
        
        model.fit(X_train)
        
        # Predict
        predictions = model.predict(X_train)
        n_anomalies = np.sum(predictions == -1)
        
        print(f"[AnomalyDetection] Local Outlier Factor trained")
        print(f"[AnomalyDetection]   - Anomalies detected: {n_anomalies}/{len(predictions)}")
        print(f"[AnomalyDetection]   - Percentage: {100*n_anomalies/len(predictions):.2f}%")
        
        return model
    
    def validate_models(self, X_test, models):
        """
        Validate trained models on test data.
        
        Parameters:
            X_test: Test data (unseen during training)
            models: Dict of trained models
        
        Returns:
            Dict of validation metrics
        """
        print("[AnomalyDetection] Validating models on test set...")
        
        results = {}
        
        for model_name, model in models.items():
            print(f"\n[AnomalyDetection] Validating {model_name}...")
            
            # Get predictions
            predictions = model.predict(X_test)
            
            # Count anomalies found
            n_anomalies = np.sum(predictions == -1)
            n_normal = np.sum(predictions == 1)
            
            results[model_name] = {
                'anomalies_found': n_anomalies,
                'normal_found': n_normal,
                'anomaly_percentage': 100 * n_anomalies / len(predictions)
            }
            
            print(f"[AnomalyDetection] {model_name} results:")
            print(f"  - Anomalies: {n_anomalies}")
            print(f"  - Normal: {n_normal}")
            print(f"  - Anomaly %: {results[model_name]['anomaly_percentage']:.2f}%")
        
        return results
    
    def save_models(self, output_dir='models/'):
        """
        Save trained models to disk for later use.
        
        Files created:
        - anomaly_isolation_forest.pkl
        - anomaly_lof.pkl
        - scaler.pkl (for scaling new data)
        - metadata.txt (training info)
        """
        print(f"[AnomalyDetection] Saving models to {output_dir}...")
        
        # Create directory if needed
        os.makedirs(output_dir, exist_ok=True)
        
        # Save models
        if self.isolation_forest:
            joblib.dump(
                self.isolation_forest,
                os.path.join(output_dir, 'anomaly_isolation_forest.pkl')
            )
            print("[AnomalyDetection] Saved Isolation Forest model")
        
        if self.lof_model:
            joblib.dump(
                self.lof_model,
                os.path.join(output_dir, 'anomaly_lof.pkl')
            )
            print("[AnomalyDetection] Saved LOF model")
        
        if self.scaler:
            joblib.dump(
                self.scaler,
                os.path.join(output_dir, 'scaler.pkl')
            )
            print("[AnomalyDetection] Saved feature scaler")
        
        # Save metadata
        with open(os.path.join(output_dir, 'metadata.txt'), 'w') as f:
            f.write(f"Training Date: {datetime.now()}\n")
            f.write(f"Models: Isolation Forest, Local Outlier Factor\n")
            f.write(f"Metrics: {self.training_metrics}\n")
    
    def train_full_pipeline(self, days=30, test_size=0.2):
        """
        Complete training pipeline from data loading to model saving.
        
        Steps:
        1. Load data from database
        2. Prepare features (clean, scale, engineer)
        3. Split into train/test sets
        4. Train models
        5. Validate models
        6. Save models
        
        Parameters:
            days: Historical data to use (default: 30)
            test_size: Fraction for testing (default: 0.2 = 20%)
        """
        print("\n" + "="*60)
        print("ANOMALY DETECTION - TRAINING PIPELINE")
        print("="*60)
        
        # Step 1: Load data
        df = self.load_data(days=days)
        if df is None:
            return False
        
        # Step 2: Prepare features
        X, feature_names, scaler = self.prepare_features(df)
        if X is None:
            return False
        
        # Step 3: Split data
        print("[AnomalyDetection] Splitting data...")
        X_train, X_test = train_test_split(
            X,
            test_size=test_size,
            random_state=42
        )
        print(f"[AnomalyDetection] Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Step 4: Train models
        print("\n[AnomalyDetection] Training models...")
        self.isolation_forest = self.train_isolation_forest(X_train)
        self.lof_model = self.train_lof(X_train)
        
        # Step 5: Validate
        print("\n[AnomalyDetection] Validating models...")
        models = {
            'Isolation Forest': self.isolation_forest,
            'Local Outlier Factor': self.lof_model
        }
        self.training_metrics = self.validate_models(X_test, models)
        
        # Step 6: Save
        print("\n[AnomalyDetection] Saving trained models...")
        self.save_models()
        
        print("\n" + "="*60)
        print("TRAINING COMPLETE!")
        print("="*60)
        return True


def main():
    """
    Main execution: Run the full anomaly detection training pipeline.
    
    This trains models on your collected metrics and saves them
    for later use in anomaly detection.
    """
    print("\n" + "="*60)
    print("WEEK 2: ANOMALY DETECTION MODEL TRAINING")
    print("="*60)
    print()
    print("This script trains anomaly detection models on your")
    print("30 days of collected system metrics.")
    print()
    print("Models trained:")
    print("  1. Isolation Forest - Finds 'outlier' data points")
    print("  2. LOF - Finds points with unusual local density")
    print()
    print("Output: Trained models saved to models/")
    print("="*60 + "\n")
    
    # Create trainer
    trainer = AnomalyDetectionTrainer()
    
    # Run full pipeline
    success = trainer.train_full_pipeline(days=30, test_size=0.2)
    
    if success:
        print("\n✅ Training successful!")
        print("Models ready for anomaly detection on new data.")
    else:
        print("\n❌ Training failed!")
        print("Check database connection and data availability.")


if __name__ == '__main__':
    main()
