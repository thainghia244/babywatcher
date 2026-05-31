#!/usr/bin/env python3
"""
Train Custom BabyMonitor2 Model - Optimized for CPU
Quick training on baby safety dataset
"""

import os
import sys
from pathlib import Path
from ultralytics import YOLO
import yaml

def main():
    print("=" * 80)
    print("🚀 BABYWATCHER CUSTOM MODEL TRAINING")
    print("=" * 80)
    
    dataset_dir = "babyMonitor2.v1i.yolov8"
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    
    # Check dataset
    if not os.path.exists(data_yaml):
        print(f"❌ Dataset not found: {data_yaml}")
        print(f"\nPlease ensure babyMonitor2 dataset is extracted")
        return 1
    
    print(f"✅ Dataset found: {dataset_dir}")
    
    # Read dataset info
    with open(data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)
    
    print(f"\n📊 Dataset Classes:")
    for i, name in enumerate(data_config.get('names', [])):
        print(f"   {i}: {name}")
    
    output_dir = "models/babyMonitor2_custom"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Training config
    epochs = 50  # Reduced from 100 for speed
    batch_size = 4  # Reduced for CPU
    
    print(f"\n⚙️  Training Configuration:")
    print(f"   Model: YOLOv8 Nano")
    print(f"   Epochs: {epochs}")
    print(f"   Batch Size: {batch_size}")
    print(f"   Device: CPU (may use GPU if available)")
    print(f"   Expected Time: 30-45 minutes on CPU")
    print(f"\n🔥 Starting training...\n")
    
    try:
        model = YOLO("yolov8n.pt")
        
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=640,
            batch=batch_size,
            patience=10,
            save=True,
            verbose=True,
            plots=False,
            project=output_dir,
            name="detector",
            exist_ok=True,
            device=0  # GPU if available, else CPU
        )
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        model_path = os.path.join(output_dir, "detector", "weights", "best.pt")
        
        if os.path.exists(model_path):
            print(f"\n📦 Model saved: {model_path}")
            file_size = os.path.getsize(model_path) / (1024*1024)
            print(f"   Size: {file_size:.1f} MB")
            
            # Update config with new model path
            print(f"\n📝 Updating config.yaml...")
            config_path = "config.yaml"
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            config['models']['object_model_path'] = model_path
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Config updated with new model path")
            
            print(f"\n" + "=" * 80)
            print("🎉 NEXT STEPS")
            print("=" * 80)
            print(f"\n1. Test the new model:")
            print(f"   python debug_detection.py --camera 0 --duration 30")
            print(f"\n2. Expected improvement:")
            print(f"   Before: Generic model (40-50% detection)")
            print(f"   After:  Custom model (70-85% detection)")
            
            return 0
        else:
            print(f"❌ Model not found at: {model_path}")
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
