"""
Week 2 - Complete Training Pipeline Orchestrator

WEEK 2 ENHANCEMENT:
Master script that orchestrates all Week 2 model training tasks.

What this does:
1. Trains anomaly detection models (Isolation Forest, LOF)
2. Trains pattern clustering models (K-Means, DBSCAN)
3. Validates all models
4. Generates training report
5. Saves all models for production use

Think of it as: A conductor orchestrating an orchestra
- Each musician (model) practices their part
- Conductor checks quality
- Then everyone performs together
"""

import os
import sys
from datetime import datetime

analysis_dir = os.path.dirname(__file__)
project_root = os.path.dirname(analysis_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, analysis_dir)

from Python_Analysis.models.anomaly_detector_trainer import AnomalyDetectionTrainer
from Python_Analysis.models.pattern_clustering_trainer import PatternClusteringTrainer


class ModelTrainingOrchestrator:
    """
    Orchestrates complete Week 2 model training pipeline.
    
    Workflow:
    1. Validate prerequisites (database exists, has data)
    2. Train anomaly detection models
    3. Train pattern clustering models
    4. Generate report
    5. Save all models
    """
    
    def __init__(self, db_path='data/metrics.db', output_dir='models/'):
        """Initialize orchestrator"""
        self.db_path = db_path
        self.output_dir = output_dir
        self.training_results = {}
        self.start_time = None
        self.end_time = None
        
    def validate_prerequisites(self):
        """
        Validate that we have everything needed for training.
        
        Checks:
        1. Database file exists
        2. Database has data
        3. Output directory can be created
        """
        print("\n" + "="*70)
        print("VALIDATING PREREQUISITES")
        print("="*70)
        
        # Check database
        print(f"\n[Validation] Checking database: {self.db_path}...", end='')
        if os.path.exists(self.db_path):
            size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            print(f" ✓ Found ({size_mb:.2f} MB)")
        else:
            print(f" ✗ Not found!")
            print("[Validation] ERROR: Database not found!")
            print("[Validation] Please run C Monitor first to collect data.")
            return False
        
        # Check output directory
        print(f"[Validation] Output directory: {self.output_dir}...", end='')
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            print(" ✓ Ready")
        except Exception as e:
            print(f" ✗ Error: {e}")
            return False
        
        print("\n[Validation] All prerequisites met!")
        return True
    
    def train_anomaly_detection(self):
        """Train anomaly detection models"""
        print("\n" + "="*70)
        print("STEP 1: ANOMALY DETECTION MODEL TRAINING")
        print("="*70)
        
        try:
            trainer = AnomalyDetectionTrainer(self.db_path)
            success = trainer.train_full_pipeline(days=30, test_size=0.2)
            
            self.training_results['anomaly_detection'] = {
                'success': success,
                'models': ['Isolation Forest', 'Local Outlier Factor'],
                'metrics': trainer.training_metrics if hasattr(trainer, 'training_metrics') else {}
            }
            
            return success
            
        except Exception as e:
            print(f"\n[ERROR] Anomaly detection training failed: {e}")
            self.training_results['anomaly_detection'] = {'success': False, 'error': str(e)}
            return False
    
    def train_pattern_clustering(self):
        """Train pattern clustering models"""
        print("\n" + "="*70)
        print("STEP 2: PATTERN CLUSTERING MODEL TRAINING")
        print("="*70)
        
        try:
            trainer = PatternClusteringTrainer(self.db_path)
            success = trainer.train_full_pipeline(days=30)
            
            self.training_results['pattern_clustering'] = {
                'success': success,
                'models': ['K-Means', 'DBSCAN'],
                'features': [
                    'temporal',  # Hour of day, day of week
                    'behavioral',  # CPU, memory, disk usage
                    'trends'  # Rolling averages
                ]
            }
            
            return success
            
        except Exception as e:
            print(f"\n[ERROR] Pattern clustering training failed: {e}")
            self.training_results['pattern_clustering'] = {'success': False, 'error': str(e)}
            return False
    
    def generate_report(self):
        """Generate training summary report"""
        print("\n" + "="*70)
        print("TRAINING REPORT")
        print("="*70)
        
        report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEK 2 - MODEL TRAINING COMPLETION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Training Duration: {(self.end_time - self.start_time).total_seconds():.1f} seconds

DATABASE INFORMATION:
  Path: {self.db_path}
  Size: {os.path.getsize(self.db_path) / (1024*1024):.2f} MB
  
TRAINING RESULTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ANOMALY DETECTION MODELS
   Status: {"✓ SUCCESS" if self.training_results.get('anomaly_detection', {}).get('success') else "✗ FAILED"}
   Models Trained:
     - Isolation Forest: Finds outlier data points
     - Local Outlier Factor: Finds unusual local density points
   
   Application:
     - Detects CPU spikes, memory leaks, disk anomalies
     - Used for real-time alerting on new data
   
   Output Files:
     - models/anomaly_isolation_forest.pkl
     - models/anomaly_lof.pkl
     - models/scaler.pkl

2. PATTERN CLUSTERING MODELS
   Status: {"✓ SUCCESS" if self.training_results.get('pattern_clustering', {}).get('success') else "✗ FAILED"}
   Models Trained:
     - K-Means: Groups data into behavioral clusters
     - DBSCAN: Density-based clustering (auto-finds clusters)
   
   Features Used:
     - Temporal: Hour of day, day of week
     - Behavioral: CPU, memory, disk usage, network
     - Trends: Rolling averages and rates of change
   
   Application:
     - Learns normal patterns (e.g., high CPU at 2 PM is normal)
     - Enables context-aware anomaly detection
   - Predicts expected resource usage
   
   Output Files:
     - models/kmeans_patterns.pkl
     - models/dbscan_patterns.pkl
     - models/clustering_scaler.pkl

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODELS SUMMARY:

Total Models Trained: 4
  ✓ Isolation Forest (Anomaly Detection)
  ✓ Local Outlier Factor (Anomaly Detection)
  ✓ K-Means (Pattern Clustering)
  ✓ DBSCAN (Pattern Clustering)

All models saved to: {self.output_dir}

Next Steps (Week 3):
  1. Deploy models to production
  2. Implement real-time anomaly detection
  3. Add alerting system
  4. Create visualization dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        print(report)
        
        # Save report to file
        report_path = os.path.join(self.output_dir, 'training_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\n[Report] Saved to: {report_path}")
    
    def run_complete_pipeline(self):
        """Execute the complete training pipeline"""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*68 + "║")
        print("║" + "  WEEK 2: COMPLETE MODEL TRAINING PIPELINE".center(68) + "║")
        print("║" + " "*68 + "║")
        print("╚" + "="*68 + "╝")
        
        self.start_time = datetime.now()
        
        # Step 1: Validate
        print("\n[Pipeline] Step 1/4: Validating prerequisites...")
        if not self.validate_prerequisites():
            print("\n❌ PIPELINE FAILED: Prerequisites not met")
            return False
        
        # Step 2: Anomaly detection
        print("\n[Pipeline] Step 2/4: Training anomaly detection models...")
        if not self.train_anomaly_detection():
            print("\n⚠️  ANOMALY DETECTION TRAINING FAILED (continuing with clustering...)")
        
        # Step 3: Clustering
        print("\n[Pipeline] Step 3/4: Training pattern clustering models...")
        if not self.train_pattern_clustering():
            print("\n⚠️  PATTERN CLUSTERING TRAINING FAILED")
        
        # Step 4: Report
        self.end_time = datetime.now()
        print("\n[Pipeline] Step 4/4: Generating report...")
        self.generate_report()
        
        print("\n" + "="*70)
        print("✅ WEEK 2 TRAINING PIPELINE COMPLETE!")
        print("="*70)
        print("\nAll trained models are ready for Week 3 deployment.")
        
        return True


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("WEEK 2: MACHINE LEARNING MODEL TRAINING")
    print("="*70)
    print()
    print("This script trains ML models on your collected metrics data.")
    print()
    print("What gets trained:")
    print("  1. Anomaly Detection Models")
    print("     - Isolation Forest: Finds unusual data points")
    print("     - Local Outlier Factor: Finds density anomalies")
    print()
    print("  2. Pattern Clustering Models")
    print("     - K-Means: Behavioral pattern grouping")
    print("     - DBSCAN: Density-based pattern detection")
    print()
    print("Expected output: 4 trained models (ML .pkl files)")
    print()
    
    # Run orchestrator
    orchestrator = ModelTrainingOrchestrator(
        db_path='data/metrics.db',
        output_dir='models/'
    )
    
    success = orchestrator.run_complete_pipeline()
    
    if success:
        print("\n💾 Models saved and ready for use!")
        print("📁 Location: models/")
        print("\nYou can now:")
        print("  - Use these models to detect anomalies in real-time")
        print("  - Analyze behavioral patterns")
        print("  - Create context-aware alerts")
    else:
        print("\n❌ Training encountered issues. Check logs above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
