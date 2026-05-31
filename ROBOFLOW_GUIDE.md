# 🤖 Roboflow Integration Guide for BabyWatcher

## Overview

BabyWatcher now integrates with **Roboflow** to help you train custom object detection models with your own dataset. This allows you to improve detection accuracy for:
- Food items (bottles, cups, spoons, etc.)
- Common household objects
- Specific items in your environment
- Region-specific objects

---

## 📋 Prerequisites

1. **Roboflow Account**: Sign up at https://roboflow.com
2. **API Key**: Get your API key from https://roboflow.com/settings/api
3. **Custom Dataset** (optional): Can be your own annotated images

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Roboflow

```bash
pip install roboflow
```

### Step 2: Configure Roboflow in config.yaml

Edit `config.yaml` and add your Roboflow credentials:

```yaml
roboflow:
  enabled: true
  api_key: "YOUR_API_KEY_HERE"  # Get from https://roboflow.com/settings/api
  workspace: "your-workspace"    # Your Roboflow workspace name
  project: "baby-safety-objects" # Your Roboflow project name
  version: 1                      # Dataset version
  
  training:
    epochs: 50
    batch_size: 16
    img_size: 640
    device: "auto"  # or "0" for GPU, "cpu" for CPU
```

### Step 3: Download & Train

```bash
# Download dataset from Roboflow
python roboflow_integration.py download

# Train custom model
python train_custom_detector.py --deploy

# Or train with custom settings
python train_custom_detector.py --epochs 100 --batch-size 32 --deploy
```

---

## 📊 Usage Examples

### Download Dataset Only

```bash
python roboflow_integration.py download --version 1 --force
```

**Output**: Dataset saved to `datasets/roboflow/v1/`

### Train Model

```bash
python train_custom_detector.py --epochs 50
```

**Process**:
1. Downloads dataset (if not exists)
2. Trains YOLOv8 Nano model
3. Saves weights to `models/custom/baby_safety_detector/weights/best.pt`

### Deploy Trained Model

```bash
python train_custom_detector.py --deploy
```

**Effect**:
- Updates `config.yaml` to use trained model
- Next run uses custom model instead of default

### List Information

```bash
# Show dataset info
python roboflow_integration.py info

# List trained models
python roboflow_integration.py list
```

---

## 📁 Project Structure

```
babywatcher/
├── roboflow_integration.py    # Roboflow API wrapper
├── train_custom_detector.py   # Training script
├── config.yaml                # Contains Roboflow config
├── datasets/
│   └── roboflow/
│       └── v1/               # Downloaded dataset
│           ├── images/
│           ├── labels/
│           └── data.yaml
├── models/
│   └── custom/
│       └── baby_safety_detector/
│           └── weights/
│               └── best.pt   # Trained model
└── logs/
    └── training_info.json    # Training metadata
```

---

## 🎯 Step-by-Step Workflow

### Phase 1: Setup Roboflow

1. Go to https://roboflow.com/
2. Create account (free tier available)
3. Create new project named "baby-safety-objects"
4. Go to Settings → API and copy your API key
5. Get your workspace name from URL: `roboflow.com/workspace/YOUR-WORKSPACE`

### Phase 2: Prepare Dataset

**Option A: Use Public Dataset**
- Roboflow has pre-made datasets for common objects
- Go to Workspace → Datasets → Browse Public Datasets
- Fork a relevant dataset (food items, household objects)

**Option B: Upload Your Own**
```bash
# Annotate images (use Roboflow Label Studio or external tool)
# Dataset structure:
# your_dataset/
# ├── images/
# │   ├── img1.jpg
# │   ├── img2.jpg
# │   └── ...
# └── labels/
#     ├── img1.xml  (or .txt for YOLO format)
#     ├── img2.xml
#     └── ...

python roboflow_integration.py upload --path /path/to/your_dataset --name "My-Baby-Safety-Dataset"
```

### Phase 3: Generate Dataset

In Roboflow Web Interface:
1. Go to your project
2. Click "Generate" → YOLOv8 format
3. Review preprocessing (augmentation, etc.)
4. Click "Generate" and wait

### Phase 4: Configure BabyWatcher

Edit `config.yaml`:

```yaml
roboflow:
  enabled: true
  api_key: "abc123..."
  workspace: "your-workspace"
  project: "baby-safety-objects"
  version: 1
```

### Phase 5: Train Model

```bash
# Option 1: Simple training
python train_custom_detector.py --deploy

# Option 2: Advanced training
python train_custom_detector.py \
  --epochs 100 \
  --batch-size 32 \
  --deploy

# Option 3: Training without deploy (test first)
python train_custom_detector.py --epochs 50
```

### Phase 6: Test Model

```bash
# Test detection with custom model
python debug_detection.py --camera 0 --duration 60

# Run full system
python main.py camera
```

---

## ⚙️ Configuration Details

### Roboflow Config Options

```yaml
roboflow:
  # API Settings
  enabled: false              # Set to true after setup
  api_key: ""                 # From https://roboflow.com/settings/api
  workspace: ""               # Your workspace name
  project: "baby-safety-objects"
  version: 1                  # Dataset version to use
  
  # Paths
  dataset_dir: "datasets/roboflow"
  trained_models_dir: "models/custom"
  
  # Training Hyperparameters
  training:
    epochs: 50                # Number of epochs (increase for better accuracy)
    batch_size: 16            # Batch size (increase for faster training, need more GPU memory)
    img_size: 640             # Image size (640 matches default YOLO)
    patience: 20              # Early stopping patience
    device: "auto"            # "auto", "0" (GPU 0), "cpu"
  
  # Upload Settings (for contributing datasets)
  upload:
    enabled: false
    local_dataset_path: ""
    dataset_name: "BabyWatcher-Custom"
    license: "CC BY 4.0"
```

### Training Hyperparameter Tips

| Parameter | Value | Notes |
|-----------|-------|-------|
| `epochs` | 50-100 | More epochs = better accuracy but slower. Start with 50. |
| `batch_size` | 8-32 | Larger = faster training but needs more GPU memory. Default 16. |
| `img_size` | 640 | Keep at 640 for YOLO compatibility. 320/480 for faster inference. |
| `patience` | 20 | Stop early if validation doesn't improve for N epochs. Prevents overfitting. |
| `device` | "auto" | Auto-selects GPU if available, falls back to CPU |

---

## 🎓 Model Training Tips

### Improve Detection Accuracy

1. **More Data**: Upload 200-500 images minimum
   - Diverse lighting conditions
   - Various angles
   - Different hand positions
   - Multiple object types

2. **Better Annotations**: Ensure bounding boxes are:
   - Tight around objects
   - Consistent across images
   - Comprehensive (no missed objects)

3. **Augmentation**: Roboflow auto-applies:
   - Rotation, flip, brightness adjustments
   - Increases training dataset 5-10x

4. **Training Settings**:
   ```bash
   # For better accuracy (slower)
   python train_custom_detector.py --epochs 100 --batch-size 32
   
   # For faster inference (less accurate)
   python train_custom_detector.py --epochs 50 --batch-size 8
   ```

### Monitor Training

Training logs saved to:
- `models/custom/baby_safety_detector/` - Training results
- `models/custom/training_info.json` - Metadata

---

## 🔍 Troubleshooting

### "Roboflow not installed"

```bash
pip install roboflow -U
```

### "API key invalid"

1. Check https://roboflow.com/settings/api
2. Ensure key is copied completely (no spaces)
3. Try regenerating a new key

### "Workspace not found"

1. Get workspace from URL: `roboflow.com/workspace/YOUR-WORKSPACE`
2. Use exact workspace name in config.yaml

### "Dataset download failed"

1. Ensure dataset is generated in Roboflow (YOLOv8 format)
2. Check internet connection
3. Verify project version exists

### "Training takes too long"

- Reduce `epochs` from 50 to 30
- Reduce `batch_size` from 16 to 8
- Use CPU training disabled: `device: "0"` for GPU

### "Out of GPU memory"

1. Reduce `batch_size` to 8 or 4
2. Use CPU training: `device: "cpu"`
3. Train on smaller image size: 416 instead of 640

---

## 📈 Deployment Workflow

After training:

1. **Auto-Deploy** (recommended):
   ```bash
   python train_custom_detector.py --deploy
   ```
   This updates config.yaml to use the trained model automatically.

2. **Manual Deploy**:
   ```bash
   # Find trained model
   python roboflow_integration.py list
   
   # Copy to config.yaml
   models:
     object_model_path: "models/custom/baby_safety_detector/weights/best.pt"
   ```

3. **A/B Testing**:
   ```bash
   # Test custom model
   cp config.yaml config_custom.yaml
   sed -i 's/yolo26n.pt/models\/custom\/baby_safety_detector\/weights\/best.pt/' config_custom.yaml
   python debug_detection.py config config_custom.yaml --camera 0 --duration 60
   ```

---

## 🌐 Advanced: Public Dataset Integration

Roboflow offers pre-made datasets you can use directly:

1. Go to https://public.roboflow.com/
2. Search for relevant datasets (e.g., "food detection", "kitchen objects")
3. Fork to your workspace
4. Use in BabyWatcher by configuring project name

**Example**: Using public food detection dataset
```yaml
roboflow:
  enabled: true
  workspace: "roboflow-universe"  # Public workspace
  project: "food-detection"       # Public project
  version: 1
```

---

## 📝 Commands Reference

```bash
# Dataset Management
python roboflow_integration.py download                # Download dataset
python roboflow_integration.py upload --path /data     # Upload dataset
python roboflow_integration.py info                    # Show dataset info
python roboflow_integration.py list                    # List trained models

# Training
python train_custom_detector.py                        # Train with defaults
python train_custom_detector.py --epochs 100          # Custom epochs
python train_custom_detector.py --batch-size 32       # Custom batch size
python train_custom_detector.py --skip-download       # Use existing dataset
python train_custom_detector.py --deploy              # Deploy after training

# Testing
python debug_detection.py --camera 0 --duration 60    # Test with custom model
python main.py camera                                  # Run full system
```

---

## ✅ Success Criteria

Your training is successful when:

✅ Dataset downloads without errors  
✅ Training completes without OOM errors  
✅ Model achieves >70% mAP on validation  
✅ `debug_detection.py` shows improved detection rate  
✅ Custom objects detected correctly with alerts  

---

## 🎯 Next Steps

1. **Create Roboflow account** if not done
2. **Set API key and workspace** in config.yaml
3. **Create/fork dataset** in Roboflow (YOLOv8 format)
4. **Run**: `python train_custom_detector.py --deploy`
5. **Test**: `python debug_detection.py --camera 0 --duration 60`

---

## 📚 Resources

- Roboflow Docs: https://docs.roboflow.com/
- YOLOv8 Training Guide: https://docs.ultralytics.com/modes/train/
- Annotation Tools: https://roboflow.com/annotate
- Public Datasets: https://public.roboflow.com/

---

**Updated**: May 26, 2026  
**Version**: 1.0  
**Status**: Ready for integration
