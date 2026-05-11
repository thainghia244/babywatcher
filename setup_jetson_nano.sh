#!/bin/bash

# BabyWatcher Jetson Nano Setup Script
# This script sets up BabyWatcher on NVIDIA Jetson Nano

set -e

echo "🚀 BabyWatcher Jetson Nano Setup"
echo "================================="

# Check if running on Jetson
if [ ! -f /proc/device-tree/model ] || ! grep -q "NVIDIA Jetson Nano" /proc/device-tree/model; then
    echo "❌ This script is designed for NVIDIA Jetson Nano only!"
    echo "Current device: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
    exit 1
fi

echo "✅ Jetson Nano detected"

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libgtk-3-dev \
    libcanberra-gtk3-module \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libtbb2 \
    libtbb-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    python3-pyqt5 \
    python3-pyqt5.qtopengl \
    qt5-default \
    libqt5opengl5-dev

# Install Jetson-specific packages
echo "🔧 Installing Jetson-specific packages..."
sudo apt install -y \
    nvidia-jetpack \
    nvidia-cuda-dev \
    nvidia-tensorrt-dev \
    nvidia-cudnn-dev

# Set Jetson to max performance mode
echo "🔌 Setting Jetson to maximum performance..."
sudo nvpmodel -m 0  # MAXN mode for Jetson Nano
sudo jetson_clocks

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --upgrade pip

# Install PyTorch for Jetson (specific version)
echo "🔥 Installing PyTorch for Jetson..."
wget https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7iml6p13fzh.whl -O torch-1.10.0-cp38-cp38-linux_aarch64.whl
pip3 install torch-1.10.0-cp38-cp38-linux_aarch64.whl
pip3 install torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/lts/1.8

# Install other dependencies
echo "📚 Installing other Python packages..."
pip3 install \
    ultralytics \
    opencv-python \
    numpy \
    pyyaml \
    pillow \
    matplotlib \
    seaborn \
    pandas \
    scipy \
    scikit-learn \
    tensorrt \
    pycuda

# Install audio libraries for Jetson
echo "🔊 Installing audio libraries..."
pip3 install \
    pydub \
    simpleaudio \
    playsound

# Create BabyWatcher directory
echo "📁 Setting up BabyWatcher directory..."
mkdir -p ~/babywatcher
cd ~/babywatcher

# Clone or copy BabyWatcher code
if [ ! -d ".git" ]; then
    echo "📥 Cloning BabyWatcher repository..."
    git clone https://github.com/your-repo/babywatcher.git .
else
    echo "📥 Pulling latest changes..."
    git pull
fi

# Create optimized config for Jetson Nano
echo "⚙️  Creating Jetson-optimized configuration..."
cat > config_jetson.yaml << EOF
# BabyWatcher Configuration for Jetson Nano

# Hardware Settings
hardware:
  platform: "jetson"
  jetson_model: "nano"
  enable_tensorrt: true
  enable_csi_camera: false
  power_mode: "maxn"

# Detection Settings
detection:
  img_size: 416  # Smaller for Jetson performance
  conf_thresh: 0.4
  hand_mouth_thresh: 45
  hand_obj_thresh: 60
  dynamic_threshold: true

# Alert Settings
alerts:
  enable_sound: true
  enable_email: false
  enable_logs: true
  danger_duration_threshold: 3.0
  danger_level:
    warning_duration: 2.0
    critical_duration: 3.0

# Model Settings
models:
  pose_model_path: "yolo26n-pose.pt"
  object_model_path: "yolo26n.pt"
  device: "cuda:0"
  half_precision: true
  max_det: 100  # Reduced for Jetson
  tensorrt_precision: "fp16"

# Performance Settings
performance:
  skip_frames: 1  # Skip every other frame for better performance
  track_fps: true
  enable_profiling: false
  batch_size: 1
  jetson_optimization: true

# Logging Settings
logging:
  log_dir: "logs"
  log_file: "events_log.csv"
  save_danger_clips: true
  clips_dir: "danger_clips"
  log_level: "INFO"

# Sound Alerts
sound:
  alert_sound_path: "sounds/alarm.wav"
  warning_sound_path: "sounds/warning.mp3"
  volume: 0.8
EOF

# Download models
echo "🤖 Downloading YOLO models..."
mkdir -p models
cd models

# Download YOLOv8 models optimized for Jetson
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

cd ..

# Create startup script
echo "🚀 Creating startup script..."
cat > start_babywatcher.sh << 'EOF'
#!/bin/bash
# BabyWatcher startup script for Jetson Nano

echo "🚀 Starting BabyWatcher on Jetson Nano..."

# Set performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Navigate to BabyWatcher directory
cd ~/babywatcher

# Run BabyWatcher with Jetson config
python3 main.py --config config_jetson.yaml "$@"
EOF

chmod +x start_babywatcher.sh

# Create service file for auto-start
echo "🔄 Creating systemd service..."
cat > babywatcher.service << EOF
[Unit]
Description=BabyWatcher AI Baby Safety Detection
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/babywatcher
ExecStart=/home/$USER/babywatcher/start_babywatcher.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo mv babywatcher.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create CSI camera setup script (optional)
echo "📷 Creating CSI camera setup script..."
cat > setup_csi_camera.sh << 'EOF'
#!/bin/bash
# Setup CSI camera for Jetson Nano

echo "📷 Setting up CSI camera..."

# Enable CSI camera in device tree
sudo /opt/nvidia/jetson-io/jetson-io.py

# Test camera
echo "Testing CSI camera..."
python3 -c "
import cv2
cap = cv2.VideoCapture('nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! nvvidconv flip-method=0 ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink')
if cap.isOpened():
    print('✅ CSI camera working!')
    ret, frame = cap.read()
    if ret:
        cv2.imwrite('csi_test.jpg', frame)
        print('📸 Test image saved as csi_test.jpg')
    cap.release()
else:
    print('❌ CSI camera not working')
"
EOF

chmod +x setup_csi_camera.sh

# Final setup instructions
echo ""
echo "🎉 BabyWatcher setup completed!"
echo "==============================="
echo ""
echo "📋 Next steps:"
echo "1. Run: ./start_babywatcher.sh"
echo "2. Or use service: sudo systemctl start babywatcher"
echo "3. For CSI camera: ./setup_csi_camera.sh"
echo ""
echo "📁 Files created:"
echo "  - config_jetson.yaml (optimized config)"
echo "  - start_babywatcher.sh (startup script)"
echo "  - setup_csi_camera.sh (CSI camera setup)"
echo ""
echo "⚡ Performance tips:"
echo "  - Use config_jetson.yaml for best performance"
echo "  - Monitor temperature: sudo nvpmodel -q"
echo "  - Check GPU usage: tegrastats"
echo ""
echo "🚀 Enjoy your AI-powered baby safety system!"