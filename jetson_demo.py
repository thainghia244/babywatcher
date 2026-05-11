#!/usr/bin/env python3
"""
BabyWatcher Jetson Nano Demo Script
Tests all Jetson-specific features and optimizations
"""

import cv2
import time
import platform
import subprocess
import sys
from pathlib import Path

def check_jetson():
    """Check if running on Jetson Nano"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            if 'jetson nano' in model:
                print("✅ Jetson Nano detected")
                return True
    except:
        pass
    print("❌ Not running on Jetson Nano")
    return False

def check_cuda():
    """Check CUDA availability"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA available: {torch.cuda.get_device_name()}")
            return True
        else:
            print("❌ CUDA not available")
            return False
    except ImportError:
        print("❌ PyTorch not installed")
        return False

def check_tensorrt():
    """Check TensorRT availability"""
    try:
        import tensorrt
        print("✅ TensorRT available")
        return True
    except ImportError:
        print("❌ TensorRT not available")
        return False

def test_camera():
    """Test camera functionality"""
    print("\n📷 Testing camera...")

    # Try CSI camera first
    try:
        cap = cv2.VideoCapture(
            'nvarguscamerasrc ! video/x-raw(memory:NVMM), ' +
            'width=1280, height=720, format=NV12, framerate=30/1 ! ' +
            'nvvidconv flip-method=0 ! video/x-raw, format=BGRx ! ' +
            'videoconvert ! video/x-raw, format=BGR ! appsink'
        )
        if cap.isOpened():
            print("✅ CSI camera working")
            ret, frame = cap.read()
            if ret:
                cv2.imwrite('csi_test.jpg', frame)
                print("📸 CSI test image saved")
            cap.release()
            return True
    except:
        print("❌ CSI camera failed")

    # Try USB camera
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("✅ USB camera working")
            ret, frame = cap.read()
            if ret:
                cv2.imwrite('usb_test.jpg', frame)
                print("📸 USB test image saved")
            cap.release()
            return True
    except:
        print("❌ USB camera failed")

    return False

def test_yolo():
    """Test YOLO model loading and inference"""
    print("\n🤖 Testing YOLO models...")

    try:
        from ultralytics import YOLO
        import torch

        # Test model loading
        print("Loading YOLOv8n-pose...")
        model = YOLO('yolo26n-pose.pt')

        # Test device
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        model.to(device)
        print(f"Model moved to {device}")

        # Test inference
        print("Testing inference...")
        results = model.predict('images/test_baby.jpg', verbose=False)
        print(f"✅ Inference successful: {len(results)} detections")

        return True

    except Exception as e:
        print(f"❌ YOLO test failed: {e}")
        return False

def test_tensorrt_conversion():
    """Test TensorRT model conversion"""
    print("\n🚀 Testing TensorRT conversion...")

    try:
        from ultralytics import YOLO

        # Load model
        model = YOLO('yolo26n-pose.pt')

        # Try TensorRT export
        print("Converting to TensorRT...")
        model.export(format='engine', device='cuda:0')

        # Load TensorRT model
        print("Loading TensorRT model...")
        trt_model = YOLO('yolo26n-pose.engine')

        # Test inference
        results = trt_model.predict('images/test_baby.jpg', verbose=False)
        print(f"✅ TensorRT inference successful: {len(results)} detections")

        return True

    except Exception as e:
        print(f"❌ TensorRT conversion failed: {e}")
        return False

def benchmark_performance():
    """Benchmark performance"""
    print("\n⚡ Performance benchmark...")

    try:
        from ultralytics import YOLO
        import time

        # Load model
        model = YOLO('yolo26n-pose.pt')
        model.to('cuda:0' if torch.cuda.is_available() else 'cpu')

        # Test on video
        cap = cv2.VideoCapture('test_video.mp4')
        if not cap.isOpened():
            print("❌ No test video found")
            return False

        frames = 0
        start_time = time.time()

        while frames < 100:  # Test 100 frames
            ret, frame = cap.read()
            if not ret:
                break

            # Resize for consistency
            frame = cv2.resize(frame, (416, 416))

            # Run inference
            results = model.predict(frame, verbose=False)
            frames += 1

        end_time = time.time()
        fps = frames / (end_time - start_time)

        print(".2f"        cap.release()
        return True

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return False

def test_audio():
    """Test audio alerts"""
    print("\n🔊 Testing audio...")

    try:
        # Try simple beep
        import winsound
        winsound.Beep(800, 300)
        print("✅ Windows audio working")
        return True
    except ImportError:
        try:
            # Try cross-platform audio
            from pydub import AudioSegment
            from pydub.playback import play
            import numpy as np

            # Generate test tone
            sample_rate = 44100
            duration = 0.3
            frequency = 800

            t = np.linspace(0, duration, int(sample_rate * duration))
            wave = np.sin(2 * np.pi * frequency * t) * 32767
            wave = wave.astype(np.int16)

            # Save and play
            test_audio = AudioSegment(
                wave.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            play(test_audio)
            print("✅ Cross-platform audio working")
            return True

        except Exception as e:
            print(f"❌ Audio test failed: {e}")
            return False

def main():
    """Main demo function"""
    print("🚀 BabyWatcher Jetson Nano Demo")
    print("=" * 40)

    # System info
    print(f"Platform: {platform.platform()}")
    print(f"Python: {sys.version}")

    # Run tests
    tests = [
        ("Jetson Detection", check_jetson),
        ("CUDA Check", check_cuda),
        ("TensorRT Check", check_tensorrt),
        ("Camera Test", test_camera),
        ("YOLO Test", test_yolo),
        ("TensorRT Conversion", test_tensorrt_conversion),
        ("Performance Benchmark", benchmark_performance),
        ("Audio Test", test_audio),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<25} {status}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{total} tests")

    if passed == total:
        print("🎉 All tests passed! Jetson Nano is ready for BabyWatcher!")
    elif passed >= total * 0.7:
        print("⚠️  Most tests passed. Some features may need attention.")
    else:
        print("❌ Many tests failed. Check setup and try again.")

    print("\n💡 Tips:")
    print("- Ensure JetPack is up to date")
    print("- Check camera connections")
    print("- Monitor temperature with 'tegrastats'")
    print("- Use 'nvpmodel -m 0' for best performance")

if __name__ == "__main__":
    main()