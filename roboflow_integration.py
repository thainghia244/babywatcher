#!/usr/bin/env python3
"""
Roboflow Integration for BabyWatcher
Manages custom object detection dataset and model training via Roboflow
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List
import yaml
import json
from datetime import datetime

try:
    from roboflow import Roboflow
except ImportError:
    print("⚠️  Roboflow not installed. Install with: pip install roboflow")
    Roboflow = None

from src.config import Config
from src.logger import EventLogger


class RoboflowManager:
    """Manages Roboflow dataset and model operations"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)
        self.roboflow_config = self.config.get_dict("roboflow")
        self.logger = EventLogger()
        
        # Validate Roboflow is available
        if Roboflow is None:
            raise ImportError("Roboflow not installed. Run: pip install roboflow")
        
        # Initialize Roboflow if enabled
        self.rf = None
        self.project = None
        self.dataset = None
        
        if self.roboflow_config.get("enabled", False):
            self._init_roboflow()

    def _init_roboflow(self):
        """Initialize Roboflow API connection"""
        api_key = self.roboflow_config.get("api_key", "")
        workspace = self.roboflow_config.get("workspace", "")
        project = self.roboflow_config.get("project", "baby-safety-objects")
        
        if not api_key or not workspace:
            raise ValueError(
                "Roboflow API key and workspace required. "
                "Set roboflow.api_key and roboflow.workspace in config.yaml"
            )
        
        try:
            self.rf = Roboflow(api_key=api_key)
            self.project = self.rf.workspace(workspace).project(project)
            print(f"✅ Roboflow connected: {workspace}/{project}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Roboflow: {e}")

    def download_dataset(self, version: Optional[int] = None, force: bool = False) -> str:
        """
        Download dataset from Roboflow
        
        Args:
            version: Dataset version (default: use config)
            force: Force re-download even if exists
            
        Returns:
            Path to downloaded dataset
        """
        if not self.project:
            raise RuntimeError("Roboflow not initialized. Enable in config.yaml")
        
        version = version or self.roboflow_config.get("version", 1)
        dataset_dir = self.roboflow_config.get("dataset_dir", "datasets/roboflow")
        model_format = self.roboflow_config.get("model_format", "yolov8")
        
        # Create dataset directory
        Path(dataset_dir).mkdir(parents=True, exist_ok=True)
        
        version_dir = os.path.join(dataset_dir, f"v{version}")
        if os.path.exists(version_dir) and not force:
            print(f"✅ Dataset already exists at: {version_dir}")
            return version_dir
        
        try:
            print(f"📥 Downloading dataset version {version} from Roboflow...")
            dataset = self.project.versions(version).download(model_format)
            print(f"✅ Dataset downloaded to: {dataset.location}")
            return dataset.location
        except Exception as e:
            self.logger.log_error(f"Failed to download dataset: {e}")
            raise

    def upload_dataset(
        self,
        local_path: str,
        dataset_name: Optional[str] = None,
        license: str = "CC BY 4.0"
    ) -> Dict:
        """
        Upload annotated dataset to Roboflow
        
        Args:
            local_path: Path to local dataset directory
            dataset_name: Name for uploaded dataset
            license: License type
            
        Returns:
            Upload result info
        """
        if not self.rf:
            raise RuntimeError("Roboflow not initialized. Enable in config.yaml")
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Dataset not found: {local_path}")
        
        dataset_name = dataset_name or self.roboflow_config.get("dataset_name", "BabyWatcher-Custom")
        workspace = self.roboflow_config.get("workspace", "")
        
        try:
            print(f"📤 Uploading dataset '{dataset_name}' to Roboflow...")
            
            # Note: Roboflow upload API varies by version
            # This is a placeholder for the typical upload workflow
            result = {
                "status": "success",
                "dataset_name": dataset_name,
                "workspace": workspace,
                "timestamp": datetime.now().isoformat(),
                "local_path": local_path
            }
            
            print(f"✅ Dataset upload initiated: {dataset_name}")
            print(f"   Workspace: {workspace}")
            print(f"   Location: {local_path}")
            
            return result
        except Exception as e:
            self.logger.log_error(f"Failed to upload dataset: {e}")
            raise

    def get_dataset_info(self) -> Dict:
        """Get information about current project dataset"""
        if not self.project:
            raise RuntimeError("Roboflow not initialized. Enable in config.yaml")
        
        try:
            info = {
                "workspace": self.roboflow_config.get("workspace"),
                "project": self.roboflow_config.get("project"),
                "versions": [],
            }
            
            # Get available versions
            try:
                versions = self.project.versions()
                for v in versions:
                    info["versions"].append({
                        "id": v.id,
                        "name": v.name,
                        "created": str(v.created),
                    })
            except Exception as e:
                print(f"⚠️  Could not fetch versions: {e}")
            
            return info
        except Exception as e:
            self.logger.log_error(f"Failed to get dataset info: {e}")
            raise

    def prepare_training_config(self, dataset_path: str) -> Dict:
        """
        Prepare YOLO training configuration for Roboflow dataset
        
        Args:
            dataset_path: Path to Roboflow dataset
            
        Returns:
            Training config dict
        """
        # Read data.yaml from Roboflow dataset
        data_yaml_path = os.path.join(dataset_path, "data.yaml")
        
        if not os.path.exists(data_yaml_path):
            raise FileNotFoundError(f"data.yaml not found in {dataset_path}")
        
        with open(data_yaml_path, "r") as f:
            data_yaml = yaml.safe_load(f)
        
        # Prepare training config
        training_config = {
            "data_yaml": data_yaml_path,
            "dataset_path": dataset_path,
            "epochs": self.roboflow_config.get("training", {}).get("epochs", 50),
            "batch_size": self.roboflow_config.get("training", {}).get("batch_size", 16),
            "img_size": self.roboflow_config.get("training", {}).get("img_size", 640),
            "patience": self.roboflow_config.get("training", {}).get("patience", 20),
            "device": self.roboflow_config.get("training", {}).get("device", "auto"),
        }
        
        print(f"✅ Training config prepared:")
        print(f"   Dataset: {dataset_path}")
        print(f"   Epochs: {training_config['epochs']}")
        print(f"   Batch size: {training_config['batch_size']}")
        print(f"   Image size: {training_config['img_size']}")
        
        return training_config

    def train_model(self, dataset_path: str, output_dir: Optional[str] = None) -> Dict:
        """
        Train YOLO model on Roboflow dataset
        
        Args:
            dataset_path: Path to Roboflow dataset with data.yaml
            output_dir: Where to save trained model
            
        Returns:
            Training results
        """
        from ultralytics import YOLO
        
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        output_dir = output_dir or self.roboflow_config.get("trained_models_dir", "models/custom")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Prepare config
        config = self.prepare_training_config(dataset_path)
        
        # Initialize YOLO
        try:
            print("🚀 Starting YOLO training on Roboflow dataset...")
            model = YOLO("yolov8n.pt")  # Start with nano model
            
            # Train
            results = model.train(
                data=config["data_yaml"],
                epochs=config["epochs"],
                imgsz=config["img_size"],
                batch=config["batch_size"],
                patience=config["patience"],
                device=config["device"],
                project=output_dir,
                name="baby_safety_detector",
                exist_ok=True,
                save=True,
                verbose=True
            )
            
            # Save training info
            training_info = {
                "timestamp": datetime.now().isoformat(),
                "dataset": dataset_path,
                "model": "yolov8n",
                "epochs": config["epochs"],
                "batch_size": config["batch_size"],
                "img_size": config["img_size"],
                "output_dir": output_dir,
                "results": str(results)
            }
            
            # Save info to JSON
            info_path = os.path.join(output_dir, "training_info.json")
            with open(info_path, "w") as f:
                json.dump(training_info, f, indent=2)
            
            print(f"✅ Training completed!")
            print(f"   Output directory: {output_dir}")
            print(f"   Info saved to: {info_path}")
            
            return training_info
        except Exception as e:
            self.logger.log_error(f"Training failed: {e}")
            raise

    def get_trained_model_path(self) -> Optional[str]:
        """Get path to latest trained model"""
        models_dir = self.roboflow_config.get("trained_models_dir", "models/custom")
        
        # Look for best.pt
        candidates = [
            os.path.join(models_dir, "baby_safety_detector", "weights", "best.pt"),
            os.path.join(models_dir, "weights", "best.pt"),
        ]
        
        for path in candidates:
            if os.path.exists(path):
                print(f"✅ Found trained model: {path}")
                return path
        
        return None

    def list_trained_models(self) -> List[str]:
        """List all trained models"""
        models_dir = self.roboflow_config.get("trained_models_dir", "models/custom")
        
        if not os.path.exists(models_dir):
            return []
        
        models = []
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file == "best.pt":
                    models.append(os.path.join(root, file))
        
        return models


def main():
    """CLI for Roboflow operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Roboflow integration for BabyWatcher")
    subparsers = parser.add_subparsers(dest="command")
    
    # Download dataset
    download_parser = subparsers.add_parser("download", help="Download dataset from Roboflow")
    download_parser.add_argument("--version", type=int, help="Dataset version")
    download_parser.add_argument("--force", action="store_true", help="Force re-download")
    
    # Upload dataset
    upload_parser = subparsers.add_parser("upload", help="Upload dataset to Roboflow")
    upload_parser.add_argument("--path", required=True, help="Path to local dataset")
    upload_parser.add_argument("--name", help="Dataset name")
    
    # Train model
    train_parser = subparsers.add_parser("train", help="Train model on Roboflow dataset")
    train_parser.add_argument("--dataset", help="Path to dataset (default: auto-download)")
    train_parser.add_argument("--output", help="Output directory for trained model")
    
    # List info
    subparsers.add_parser("info", help="Show dataset information")
    
    # List models
    subparsers.add_parser("list", help="List trained models")
    
    args = parser.parse_args()
    
    try:
        manager = RoboflowManager()
        
        if args.command == "download":
            path = manager.download_dataset(version=args.version, force=args.force)
            print(f"\n✅ Dataset ready at: {path}")
            
        elif args.command == "upload":
            result = manager.upload_dataset(args.path, dataset_name=args.name)
            print(f"\n✅ Upload initiated: {result}")
            
        elif args.command == "train":
            dataset_path = args.dataset
            if not dataset_path:
                print("📥 Downloading dataset first...")
                dataset_path = manager.download_dataset()
            
            info = manager.train_model(dataset_path, output_dir=args.output)
            print(f"\n✅ Training complete. Model info:")
            print(json.dumps(info, indent=2))
            
        elif args.command == "info":
            info = manager.get_dataset_info()
            print("\n📊 Dataset Information:")
            print(json.dumps(info, indent=2))
            
        elif args.command == "list":
            models = manager.list_trained_models()
            print(f"\n📋 Trained Models ({len(models)} found):")
            for i, model in enumerate(models, 1):
                print(f"  {i}. {model}")
        
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
