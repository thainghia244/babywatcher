#!/usr/bin/env python3
"""
Training script using Roboflow dataset
Downloads dataset, trains custom YOLO model, and deploys to detector
"""

import os
import sys
import argparse
from pathlib import Path

from roboflow_integration import RoboflowManager
from src.config import Config
from src.logger import EventLogger


def main():
    parser = argparse.ArgumentParser(
        description="Train custom object detector using Roboflow dataset"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip dataset download (use existing)",
    )
    parser.add_argument(
        "--version",
        type=int,
        help="Roboflow dataset version",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        help="Override training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Override batch size",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy trained model after training",
    )
    
    args = parser.parse_args()
    
    logger = EventLogger()
    config = Config("config.yaml")
    
    try:
        # Initialize Roboflow manager
        print("=" * 80)
        print("🚀 BABYWATCHER CUSTOM MODEL TRAINING")
        print("=" * 80)
        
        manager = RoboflowManager()
        
        # Step 1: Download dataset
        print("\n📥 STEP 1: Dataset Management")
        print("-" * 80)
        
        if args.skip_download:
            print("⏭️  Skipping download (using existing dataset)")
            # Try to find existing dataset
            dataset_dir = manager.roboflow_config.get("dataset_dir", "datasets/roboflow")
            version = args.version or manager.roboflow_config.get("version", 1)
            dataset_path = os.path.join(dataset_dir, f"v{version}")
            
            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Dataset not found at {dataset_path}")
        else:
            version = args.version
            dataset_path = manager.download_dataset(version=version)
        
        print(f"✅ Dataset ready: {dataset_path}")
        
        # Step 2: Configure training
        print("\n⚙️  STEP 2: Training Configuration")
        print("-" * 80)
        
        config_dict = manager.prepare_training_config(dataset_path)
        
        # Override with CLI args
        if args.epochs:
            config_dict["epochs"] = args.epochs
        if args.batch_size:
            config_dict["batch_size"] = args.batch_size
        
        print(f"Configuration:")
        for key, value in config_dict.items():
            if key != "data_yaml":
                print(f"  {key}: {value}")
        
        # Step 3: Train model
        print("\n🔥 STEP 3: Model Training")
        print("-" * 80)
        
        training_info = manager.train_model(
            dataset_path,
            output_dir=manager.roboflow_config.get("trained_models_dir")
        )
        
        # Step 4: Deploy model (optional)
        if args.deploy:
            print("\n📦 STEP 4: Deployment")
            print("-" * 80)
            
            model_path = manager.get_trained_model_path()
            if model_path:
                print(f"✅ Trained model found: {model_path}")
                
                # Update config to use custom model
                config_dict = config.get_dict()
                config_dict["models"]["object_model_path"] = model_path
                
                # Save updated config
                import yaml
                with open("config.yaml", "w") as f:
                    yaml.dump(config_dict, f)
                
                print(f"✅ Config updated to use custom model")
                print(f"   Next run will use: {model_path}")
            else:
                print("⚠️  Trained model not found")
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Test the model: python debug_detection.py --camera 0 --duration 60")
        print("  2. Run full system: python main.py camera")
        
        return 0
        
    except Exception as e:
        logger.log_error(f"Training failed: {e}")
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
