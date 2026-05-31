#!/usr/bin/env python3
"""
BabyWatcher System Comprehensive Audit Report
Detailed review of all system components
"""

import os
import yaml
import subprocess
from datetime import datetime
from pathlib import Path

def check_file(filepath):
    """Check if file exists and return size"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        if size > 1024*1024:
            return f"✅ ({size/(1024*1024):.1f}MB)"
        else:
            return f"✅ ({size/1024:.1f}KB)"
    return "❌ MISSING"

def count_files(directory):
    """Count files in directory"""
    if not os.path.exists(directory):
        return 0
    return len([f for f in Path(directory).rglob('*') if f.is_file()])

def get_config_value(key, default="N/A"):
    """Get config value safely"""
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        keys = key.split('.')
        value = config
        for k in keys:
            value = value.get(k, {})
        return value if value else default
    except:
        return default

def main():
    print("\n")
    print("=" * 90)
    print("🔍 BABYWATCHER COMPREHENSIVE SYSTEM AUDIT")
    print("=" * 90)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. CORE MODELS
    print("📦 1. CORE MODELS & WEIGHTS")
    print("-" * 90)
    models = {
        "Object Detection": "yolo26n.pt",
        "Pose Estimation": "yolo26n-pose.pt",
    }
    for name, path in models.items():
        status = check_file(path)
        print(f"   {name:20} {path:20} {status}")
    
    # 2. SOURCE CODE
    print("\n💻 2. SOURCE CODE MODULES")
    print("-" * 90)
    src_files = {
        "Main Entry": "main.py",
        "Detection Engine": "src/detector.py",
        "Alert Manager": "src/alerts.py",
        "Event Logger": "src/logger.py",
        "Config Manager": "src/config.py",
        "Utilities": "src/utils.py",
        "Performance Monitor": "src/performance.py",
        "Debug Tool": "debug_detection.py",
    }
    for name, path in src_files.items():
        status = check_file(path)
        print(f"   {name:20} {path:30} {status}")
    
    # 3. CONFIGURATION
    print("\n⚙️  3. CONFIGURATION STATUS")
    print("-" * 90)
    
    config_items = {
        "Configuration File": "config.yaml",
        "Requirements File": "requirements.txt",
    }
    for name, path in config_items.items():
        status = check_file(path)
        print(f"   {name:25} {status}")
    
    print("\n   Detection Settings:")
    print(f"      • Confidence Threshold:        {get_config_value('detection.conf_thresh')}")
    print(f"      • Small Object Threshold:      {get_config_value('detection.small_object_conf_thresh')}")
    print(f"      • Hand-Mouth Multiplier:       {get_config_value('detection.hand_mouth_multiplier')}")
    print(f"      • Hand-Object Multiplier:      {get_config_value('detection.hand_object_multiplier')}")
    print(f"      • Dynamic Threshold:           {get_config_value('detection.dynamic_threshold')}")
    
    print("\n   Alert Settings:")
    print(f"      • Danger Duration Threshold:   {get_config_value('alerts.danger_duration_threshold')}s")
    print(f"      • Sound Alerts Enabled:        {get_config_value('alerts.enable_sound')}")
    print(f"      • Email Alerts Enabled:        {get_config_value('email.enabled')}")
    print(f"      • Logging Enabled:             {get_config_value('alerts.enable_logs')}")
    
    print("\n   Model Paths:")
    print(f"      • Object Model:                {get_config_value('models.object_model_path')}")
    print(f"      • Pose Model:                  {get_config_value('models.pose_model_path')}")
    print(f"      • Hand Model:                  {get_config_value('models.hand_model_path')}")
    
    # 4. DATA DIRECTORIES
    print("\n📁 4. DATA STORAGE & LOGGING")
    print("-" * 90)
    
    dirs = {
        "Logs Directory": "logs",
        "Danger Clips": "danger_clips",
        "Sample Images": "images",
        "Sound Files": "sounds",
    }
    
    for name, path in dirs.items():
        if os.path.exists(path):
            count = count_files(path)
            size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                      for dirpath, dirnames, filenames in os.walk(path)
                      for filename in filenames) / (1024*1024)
            status = f"✅ ({count} files, {size:.1f}MB)"
        else:
            status = "⚠️  Not created yet"
        print(f"   {name:20} {path:20} {status}")
    
    # 5. EVENT LOGS
    print("\n📊 5. EVENT LOGS & STATISTICS")
    print("-" * 90)
    
    if os.path.exists("logs/events_log.csv"):
        with open("logs/events_log.csv", 'r') as f:
            lines = f.readlines()
        
        # Count events by type
        hand_to_mouth = len([l for l in lines if "HAND_TO_MOUTH" in l])
        object_to_mouth = len([l for l in lines if "OBJECT_TO_MOUTH" in l])
        
        print(f"   Event Log File:                ✅ {len(lines)-1} total events")
        print(f"      • Hand-to-Mouth Alerts:     {hand_to_mouth}")
        print(f"      • Object-to-Mouth Alerts:   {object_to_mouth}")
        
        # Get last 3 events
        if len(lines) > 1:
            print(f"\n   Last 3 Events:")
            for line in lines[-3:]:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    print(f"      • {parts[1]:20} | {parts[2]:20} | Duration: {parts[3]}s")
    else:
        print(f"   Event Log:                     ⚠️  No events logged yet")
    
    # 6. DATASET
    print("\n🎯 6. DATASET FOR CUSTOM TRAINING")
    print("-" * 90)
    
    dataset_path = "babyMonitor2.v1i.yolov8"
    if os.path.exists(dataset_path):
        data_yaml = os.path.join(dataset_path, "data.yaml")
        try:
            with open(data_yaml, 'r') as f:
                data = yaml.safe_load(f)
            
            classes = data.get('names', [])
            nc = data.get('nc', 0)
            
            print(f"   Dataset:                       ✅ {dataset_path}")
            print(f"      • Classes: {nc}")
            for i, cls in enumerate(classes):
                print(f"         {i+1}. {cls}")
            
            # Count images
            train_imgs = len([f for f in Path(f"{dataset_path}/train/images").glob("*.*")]) if Path(f"{dataset_path}/train/images").exists() else 0
            val_imgs = len([f for f in Path(f"{dataset_path}/valid/images").glob("*.*")]) if Path(f"{dataset_path}/valid/images").exists() else 0
            test_imgs = len([f for f in Path(f"{dataset_path}/test/images").glob("*.*")]) if Path(f"{dataset_path}/test/images").exists() else 0
            
            print(f"\n   Dataset Split:")
            print(f"      • Training:   {train_imgs} images")
            print(f"      • Validation: {val_imgs} images")
            print(f"      • Testing:    {test_imgs} images")
            print(f"      • Total:      {train_imgs + val_imgs + test_imgs} images")
            
        except:
            print(f"   Dataset:                       ⚠️  Found but error reading metadata")
    else:
        print(f"   Dataset:                       ⚠️  Not available")
    
    # 7. TRAINING TOOLS
    print("\n🚀 7. TRAINING & DEPLOYMENT TOOLS")
    print("-" * 90)
    
    tools = {
        "Custom Model Training": "train_custom_model.py",
        "Quick Training (CPU)": "train_quick.py",
        "Email Configuration": "configure_email.py",
        "Object Test Guide": "TEST_OBJECTS.md",
        "Roboflow Integration": "roboflow_integration.py",
    }
    
    for name, path in tools.items():
        status = check_file(path)
        print(f"   {name:30} {status}")
    
    # 8. DEPENDENCIES
    print("\n📚 8. PYTHON DEPENDENCIES")
    print("-" * 90)
    
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", 'r') as f:
            reqs = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
        
        print(f"   Total Dependencies: {len(reqs)}")
        print(f"\n   Key Packages:")
        key_packages = ['ultralytics', 'torch', 'opencv', 'numpy', 'pyyaml', 'roboflow']
        for req in reqs:
            for key in key_packages:
                if key.lower() in req.lower():
                    print(f"      ✅ {req}")
                    break
    
    # 9. SYSTEM STATUS
    print("\n✅ 9. SYSTEM HEALTH CHECK")
    print("-" * 90)
    
    checks = {
        "All core models present": os.path.exists("yolo26n.pt") and os.path.exists("yolo26n-pose.pt"),
        "Configuration valid": os.path.exists("config.yaml"),
        "Source code complete": all(os.path.exists(f) for f in src_files.values()),
        "Logging system ready": os.path.exists("logs") and os.path.exists("logs/events_log.csv"),
        "Alert system ready": get_config_value('alerts.enable_sound') in [True, 'true'],
        "Danger clip saving": os.path.exists("danger_clips") and count_files("danger_clips") > 0,
        "Dataset available": os.path.exists("babyMonitor2.v1i.yolov8"),
        "Training tools ready": os.path.exists("train_custom_model.py"),
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check, status in checks.items():
        symbol = "✅" if status else "⚠️ "
        print(f"   {symbol} {check}")
    
    print(f"\n   Overall Status: {passed}/{total} checks passed")
    
    if passed == total:
        print(f"   🎉 SYSTEM IS FULLY OPERATIONAL\n")
    elif passed >= total - 2:
        print(f"   ⚠️  SYSTEM IS MOSTLY OPERATIONAL - Minor issues\n")
    else:
        print(f"   ❌ SYSTEM HAS ISSUES - Review configuration\n")
    
    # 10. RECOMMENDED ACTIONS
    print("💡 10. RECOMMENDED NEXT ACTIONS")
    print("-" * 90)
    
    recommendations = []
    
    if not get_config_value('email.enabled'):
        recommendations.append("• Configure email alerts: python configure_email.py")
    
    if not os.path.exists("babyMonitor2.v1i.yolov8"):
        recommendations.append("• Dataset not available - Download from Roboflow")
    
    if os.path.exists("babyMonitor2.v1i.yolov8") and not os.path.exists("models/babyMonitor2_custom"):
        recommendations.append("• Train custom model: python train_custom_model.py (30-45 min)")
    
    if count_files("danger_clips") < 5:
        recommendations.append("• Test object detection with real items: python debug_detection.py --camera 0 --duration 60")
    
    if not recommendations:
        recommendations.append("• All systems operational - ready for continuous monitoring")
        recommendations.append("• Optionally: Train custom model for improved accuracy")
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n" + "=" * 90)
    print("End of System Audit Report")
    print("=" * 90 + "\n")

if __name__ == "__main__":
    main()
