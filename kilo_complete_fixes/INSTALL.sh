#!/bin/bash

# Complete Kilo Truck Fixes Installation
# For Raspberry Pi 4 + Debian Trixie

set -e

echo "🔧 Installing complete Kilo Truck fixes..."

INSTALL_DIR="/opt/kilo"
cd "$INSTALL_DIR"

# 1. Install permanent pip fix (resolves externally-managed-environment)
echo "📦 Installing permanent pip fix..."
sudo ./install_permanent_pip_fix.sh

# 2. Install personality dependencies
echo "🎭 Installing personality system dependencies..."
sudo ./fix_pi4_trixie_personality.sh

# 3. Install fixed Android IMU module
echo "📱 Installing fixed Android IMU module..."
sudo cp fixed_android_imu_v2.py /opt/kilo/bin/
sudo chmod +x /opt/kilo/bin/fixed_android_imu_v2.py

# 4. Install ackermann module
echo "🚗 Installing ackermann PWM base module..."
sudo mkdir -p /opt/kilo/modules/ackermann-pwm-base
sudo cp -r modules/ackermann-pwm-base/* /opt/kilo/modules/ackermann-pwm-base/
sudo chmod +x /opt/kilo/modules/ackermann-pwm-base/ackermann

# 5. Install personality daemon
echo "🤖 Installing personality daemon..."
sudo cp personality/personalityd.py /opt/kilo/bin/
sudo chmod +x /opt/kilo/bin/personalityd.py
sudo mkdir -p /opt/kilo/personality

# 6. Install bridge files
echo "🌉 Installing Android bridge files..."
sudo mkdir -p /opt/kilo/bridges
sudo cp bridges/*.py /opt/kilo/bridges/
sudo chmod +x /opt/kilo/bridges/*.py

# 7. Install systemd services
echo "🔧 Installing systemd services..."
sudo cp systemd_services/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# 8. Enable and start core services
echo "🚀 Enabling and starting services..."
sudo systemctl enable kilo-android-imu kilo-personality kilo-ackermann
sudo systemctl enable android_eyes_bridge android_face_bridge android_audio_bridge

echo ""
echo "✅ Complete Kilo Truck fixes installed!"
echo ""
echo "Services installed:"
systemctl list-unit-files | grep -E "(kilo|android)" | grep enabled
echo ""
echo "Next steps:"
echo "  1. Connect Pixel 4a via USB and enable tethering"
echo "  2. Start services: sudo systemctl start kilo-android-imu kilo-personality"
echo "  3. Check status: sudo systemctl status kilo-android-imu"
echo "  4. View logs: sudo journalctl -u kilo-android-imu -f"
echo ""
echo "All compatibility issues for Pi 4 + Trixie should now be resolved!"