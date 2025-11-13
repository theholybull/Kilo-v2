#!/bin/bash

# Fix for Debian Trixie on Raspberry Pi 4 - Personality System
# Addresses externall-managed-environment and ARM64 compilation issues

set -e

echo "🔧 Fixing personality system for Debian Trixie on Pi 4..."

# Ensure we're running in correct directory
INSTALL_DIR="/opt/kilo"
cd "$INSTALL_DIR"

# Check if venv exists, if not create it properly
if [ ! -d "venv" ]; then
    echo "🏗️ Creating Python virtual environment for Trixie..."
    python3-full -m venv venv || python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Update pip in venv
echo "📦 Updating pip..."
pip install --upgrade pip setuptools wheel

# Install system dependencies for Pi 4 on Trixie
echo "🔊 Installing ARM64 audio dependencies..."
sudo apt-get update
sudo apt-get install -y \
    portaudio19-dev \
    python3-full \
    python3-dev \
    gcc \
    g++ \
    make \
    libasound2-dev \
    libjack-jackd2-0 \
    libjack-jackd2-dev \
    libsamplerate0-dev \
    libsndfile1-dev \
    build-essential \
    pkg-config \
    libffi-dev \
    libopus0 \
    libopus-dev

# Install packages in venv with ARM64 compatibility
echo "📚 Installing Python packages in venv..."

# Install basic packages first
pip install --upgrade setuptools wheel

# Install packages with specific versions for ARM64/Trixie
echo "Installing vosk (ARM64 compatible)..."
pip install --no-cache-dir vosk==0.3.45 || {
    echo "Trying alternative vosk installation..."
    pip install --no-cache-dir --force-reinstall vosk
}

echo "Installing sounddevice..."
pip install --no-cache-dir sounddevice || {
    echo "Trying alternative sounddevice installation..."
    pip install --no-cache-dir --force-reinstall sounddevice
}

echo "Installing webrtcvad..."
pip install --no-cache-dir webrtcvad==2.0.10 || {
    echo "Trying alternative webrtcvad installation..."
    pip install --no-cache-dir --force-reinstall webrtcvad
}

# Install additional dependencies
echo "Installing additional packages..."
pip install --no-cache-dir \
    requests \
    websockets \
    aiohttp \
    flask \
    flask-socketio \
    pyyaml \
    click \
    colorama

# Test imports
echo "🧪 Testing imports..."
python3 -c "
try:
    import vosk
    print('✅ vosk imported')
except Exception as e:
    print(f'❌ vosk failed: {e}')

try:
    import sounddevice
    print('✅ sounddevice imported') 
except Exception as e:
    print(f'❌ sounddevice failed: {e}')

try:
    import webrtcvad
    print('✅ webrtcvad imported')
except Exception as e:
    print(f'❌ webrtcvad failed: {e}')
"

# Install personality files
echo "🎭 Installing personality files..."
sudo mkdir -p /opt/kilo/personality/sounds
sudo mkdir -p /opt/kilo/personality/config

if [ -f "kilo-complete-system-clean/kilo/personality/personalityd.py" ]; then
    sudo cp kilo-complete-system-clean/kilo/personality/personalityd.py /opt/kilo/bin/
    sudo chmod +x /opt/kilo/bin/personalityd.py
    echo "✅ personalityd.py installed"
else
    echo "❌ personalityd.py not found"
fi

if [ -d "kilo-complete-system-clean/kilo/personality/sounds" ]; then
    sudo cp -r kilo-complete-system-clean/kilo/personality/sounds/* /opt/kilo/personality/sounds/
    echo "✅ sounds installed"
fi

if [ -f "kilo-complete-system-clean/kilo/personality/persona.json" ]; then
    sudo cp kilo-complete-system-clean/kilo/personality/*.json /opt/kilo/personality/config/
    sudo cp kilo-complete-system-clean/kilo/personality/*.yaml /opt/kilo/personality/config/
    echo "✅ config files installed"
fi

echo "✅ Pi 4 Trixie personality fix complete!"
echo ""
echo "Test with:"
echo "  source /opt/kilo/venv/bin/activate"
echo "  python3 /opt/kilo/bin/personalityd.py"