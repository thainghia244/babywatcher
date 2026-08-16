#!/usr/bin/env python3
"""
Fast training script for babyMonitor2 - optimized for quick results
"""

import os
import sys
from pathlib import Path
from ultralytics import YOLO
import yaml

def main():
    print("=" * 80)
    print("🚀 BABYWATCHER QUICK TRAINING - babyMonitor2")
    print("=" * 80)
    
    # 3-class version (baby, blanket, toy) with the near-empty 'other' class
    # (5 instances total) dropped -- see fix_class_imbalance.py -- merged with
    # 3 supplementary public datasets (Baby Monitoring 4, Baby-Detection,
    # kid-toys) and re-split 80/10/10 -- see merge_datasets.py.
    dataset_dir = "babyMonitor2_merged.v1i.yolov8"
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    
    if not os.path.exists(data_yaml):
        print(f"❌ Dataset not found: {data_yaml}")
        sys.exit(1)
    
    print(f"✅ Dataset found: {dataset_dir}")
    
    # Read dataset info
    with open(data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)
    
    print(f"\n📊 Dataset Info:")
    print(f"   Classes: {data_config.get('nc', 'N/A')}")
    print(f"   Names: {data_config.get('names', 'N/A')}")
    
    output_dir = "models/babyMonitor2"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"\n⚙️  QUICK TRAINING (CPU optimized):")
    print(f"   Model: YOLOv8 Nano")
    print(f"   Epochs: 30 (fast training)")
    print(f"   Batch Size: 8 (CPU friendly)")
    print(f"   Device: CPU")
    print(f"\n🔥 Starting training...\n")
    
    try:
        model = YOLO("yolov8n.pt")
        
        results = model.train(
            data=data_yaml,
            epochs=30,  # Quick training
            imgsz=640,
            batch=8,    # Small batch for CPU
            patience=10,
            device="cpu",  # Force CPU
            project=output_dir,
            name="detector",
            exist_ok=True,
            save=True,
            verbose=False,
            plots=False
        )
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETED!")
        print("=" * 80)
        
        model_path = os.path.join(output_dir, "detector", "weights", "best.pt")
        
        if os.path.exists(model_path):
            print(f"\n✅ Model saved: {model_path}")
            file_size = os.path.getsize(model_path) / (1024*1024)
            print(f"   Size: {file_size:.1f} MB")
            
            # Update config
            print(f"\n📝 Updating config.yaml...")
            config_path = "config.yaml"
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            config['models']['object_model_path'] = model_path
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Config updated!")
            
            print(f"\n" + "=" * 80)
            print("🎉 READY TO TEST!")
            print("=" * 80)
            print(f"\nRun this to test:")
            print(f"  python debug_detection.py --camera 0 --duration 30")
            
            return 0
        else:
            print(f"❌ Model not found: {model_path}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
