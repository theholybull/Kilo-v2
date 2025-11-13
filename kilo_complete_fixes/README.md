# Kilo Truck Complete Fixes Package

This package contains all working fixes for the specific issues encountered during setup on Raspberry Pi 4 + Debian Trixie.

## Issues Fixed

### 1. Android IMU SUBTYPE Error
**Problem**: `AttributeError: module 'viam.components.movement_sensor' has no attribute 'SUBTYPE'`
**Fix**: `fixed_android_imu_v2.py` - Uses MovementSensor.API instead of SUBTYPE

### 2. Ackermann Module Import Error  
**Problem**: "unknown resource type: API rdk:component:movement_sensor with model kilo:movement_sensor:oak-bmi270 not registered"
**Fix**: Complete corrected ackermann module with proper Go module structure

### 3. Personality System Dependencies
**Problem**: Missing system dependencies and build failures for vosk, sounddevice, webrtcvad
**Fix**: `fix_pi4_trixie_personality.sh` - Installs all ARM64 compatible dependencies

### 4. Externally-Managed-Environment Error
**Problem**: `error: externally-managed-environment` when installing Python packages
**Fix**: `install_permanent_pip_fix.sh` - Creates pip/python wrappers enforcing venv usage

### 5. Bridge Import Errors
**Problem**: Missing aiohttp and other dependencies for Android bridge files
**Fix**: All bridge files with proper imports and systemd services

## Installation

1. Extract this package to `/opt/kilo/`
2. Run fixes in order:
   ```bash
   sudo ./install_permanent_pip_fix.sh
   sudo ./fix_pi4_trixie_personality.sh
   sudo cp systemd_services/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

## Files Included

### Core Fixes
- `fixed_android_imu_v2.py` - Corrected Android IMU module
- `install_permanent_pip_fix.sh` - Permanent pip error fix
- `fix_pi4_trixie_personality.sh` - Personality dependencies
- `pi4_trixie_requirements.txt` - Compatible package versions

### Systemd Services
- `kilo-android-imu.service` - Android IMU service
- `kilo-personality.service` - Personality daemon service  
- `kilo-ackermann.service` - Ackermann module service
- All bridge services (android_*_bridge.service)

### Bridge Files
- All Android bridge files with proper imports
- Working versions with aiohttp dependencies

This package provides complete solutions for all Pi 4 + Trixie compatibility issues encountered.