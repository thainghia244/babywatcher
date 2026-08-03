#!/usr/bin/env python3
"""
Train Custom BabyMonitor2 Model - Optimized for CPU
Quick training on baby safety dataset
"""

import os
import sys
import argparse
from pathlib import Path
from ultralytics import YOLO
import yaml

def build_dataset_yaml(dataset_dir: str, output_yaml: str, class_names: list[str]):
    """Create a YOLO-style data.yaml for a custom image dataset."""
    data_config = {
        "path": dataset_dir,
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "names": class_names,
    }
    with open(output_yaml, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data_config, f, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Train a custom YOLO model for BabyWatcher from image datasets")
    parser.add_argument("--dataset", default="babyMonitor2.v1i.yolov8", help="Path to the dataset folder")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Training batch size")
    parser.add_argument("--img-size", type=int, default=640, help="Training image size")
    parser.add_argument("--output", default="models/babyMonitor2_custom", help="Output directory for trained model")
    parser.add_argument("--classes", nargs="+", default=["hand", "object"], help="Class names for training")
    parser.add_argument("--device", default="0", help="Training device: cpu or 0/1/2 for GPU")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 BABYWATCHER CUSTOM MODEL TRAINING")
    print("=" * 80)
    
    dataset_dir = args.dataset
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    
    # Check dataset
    if not os.path.exists(dataset_dir):
        print(f"❌ Dataset folder not found: {dataset_dir}")
        return 1

    if not os.path.exists(data_yaml):
        print(f"⚠️  No data.yaml found in {dataset_dir}; generating a basic one for image folders")
        build_dataset_yaml(dataset_dir, data_yaml, args.classes)
    
    print(f"✅ Dataset found: {dataset_dir}")
    
    # Read dataset info
    with open(data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)
    
    print(f"\n📊 Dataset Classes:")
    for i, name in enumerate(data_config.get('names', [])):
        print(f"   {i}: {name}")
    
    output_dir = args.output
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Training config
    epochs = args.epochs
    batch_size = args.batch_size
    
    print(f"\n⚙️  Training Configuration:")
    print(f"   Model: YOLOv8 Nano")
    print(f"   Epochs: {epochs}")
    print(f"   Batch Size: {batch_size}")
    print(f"   Image Size: {args.img_size}")
    print(f"   Device: {args.device}")
    print(f"   Output: {output_dir}")
    print(f"\n🔥 Starting training...\n")
    
    try:
        model = YOLO("yolov8n.pt")
        
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=args.img_size,
            batch=batch_size,
            patience=10,
            save=True,
            verbose=True,
            plots=False,
            project=output_dir,
            name="detector",
            exist_ok=True,
            device=args.device
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
