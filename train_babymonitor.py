#!/usr/bin/env python3
"""
Train custom YOLOv8 model from babyMonitor2 dataset
Integrated training script for BabyWatcher
"""

import os
import sys
from pathlib import Path
from ultralytics import YOLO
import yaml

def main():
    print("=" * 80)
    print("🚀 BABYWATCHER CUSTOM MODEL TRAINING - babyMonitor2")
    print("=" * 80)
    
    # Dataset path
    dataset_dir = "babyMonitor2.v1i.yolov8"
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    
    # Check dataset exists
    if not os.path.exists(data_yaml):
        print(f"❌ Dataset not found: {data_yaml}")
        sys.exit(1)
    
    print(f"\n✅ Dataset found: {dataset_dir}")
    
    # Read dataset info
    with open(data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)
    
    print(f"\n📊 Dataset Info:")
    print(f"   Classes: {data_config.get('nc', 'N/A')}")
    print(f"   Names: {data_config.get('names', 'N/A')}")
    
    # Create output directory
    output_dir = "models/babyMonitor2"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"\n⚙️  Training Configuration:")
    print(f"   Dataset: {data_yaml}")
    print(f"   Output: {output_dir}")
    print(f"   Model: YOLOv8 Nano")
    print(f"   Epochs: 100")
    print(f"   Image Size: 640")
    print(f"   Batch Size: 16")
    
    print(f"\n🔥 Starting training...")
    print("   (This may take 10-30 minutes depending on GPU)")
    print()
    
    try:
        # Load model
        model = YOLO("yolov8n.pt")  # nano model
        
        # Train
        results = model.train(
            data=data_yaml,
            epochs=100,
            imgsz=640,
            batch=16,
            patience=20,
            device=0,  # GPU 0, or "cpu" for CPU-only
            project=output_dir,
            name="detector",
            exist_ok=True,
            save=True,
            verbose=True,
            plots=True
        )
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETED!")
        print("=" * 80)
        
        # Find trained model
        model_path = os.path.join(output_dir, "detector", "weights", "best.pt")
        
        if os.path.exists(model_path):
            print(f"\n✅ Trained model saved: {model_path}")
            
            # Update config.yaml
            print(f"\n📝 Updating config.yaml...")
            config_path = "config.yaml"
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update model path
            config['models']['object_model_path'] = model_path
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Config updated to use: {model_path}")
            
            print(f"\n" + "=" * 80)
            print("🎉 INTEGRATION COMPLETE!")
            print("=" * 80)
            print(f"\nNext steps:")
            print(f"  1. Test detection:")
            print(f"     python debug_detection.py --camera 0 --duration 60")
            print(f"\n  2. Run full system:")
            print(f"     python main.py camera")
            
            return 0
        else:
            print(f"\n❌ Model not found at expected location: {model_path}")
            print(f"   Check {output_dir} directory")
            return 1
            
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
