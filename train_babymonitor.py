#!/usr/bin/env python3
"""
Train custom YOLOv8 model from babyMonitor2 dataset
Integrated training script for BabyWatcher
"""

import argparse
import os
import sys
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO


def resolve_device(requested_device):
    if requested_device in (None, "", "auto"):
        return "0" if torch.cuda.is_available() else "cpu"

    if str(requested_device) == "0" and not torch.cuda.is_available():
        print("⚠️ GPU not available, falling back to CPU")
        return "cpu"

    return requested_device


def main():
    parser = argparse.ArgumentParser(description="Train custom YOLOv8 model for BabyWatcher")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    print("=" * 80)
    print("🚀 BABYWATCHER CUSTOM MODEL TRAINING - babyMonitor2")
    print("=" * 80)
    
    # Dataset path
    # 3-class version (baby, blanket, toy) with the near-empty 'other' class
    # (5 instances total) dropped -- see fix_class_imbalance.py -- merged with
    # 3 supplementary public datasets (Baby Monitoring 4, Baby-Detection,
    # kid-toys) and re-split 80/10/10 -- see merge_datasets.py.
    dataset_dir = "babyMonitor2_merged.v1i.yolov8"
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
    device = resolve_device(args.device)
    print(f"   Epochs: {args.epochs}")
    print(f"   Image Size: {args.imgsz}")
    print(f"   Batch Size: {args.batch}")
    print(f"   Device: {device}")
    
    print(f"\n🔥 Starting training...")
    print("   (This may take 10-30 minutes depending on GPU)")
    print()
    
    try:
        # Load model
        model = YOLO("yolov8n.pt")  # nano model
        
        # Train
        results = model.train(
            data=data_yaml,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=20,
            device=device,
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
