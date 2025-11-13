#!/usr/bin/env python3
"""
Fixed Android IMU Module for Viam
Corrected to use MovementSensor.API instead of SUBTYPE
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

import requests
from viam.components.movement_sensor import MovementSensor
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import GeoPoint, Orientation, Vector3
from viam.resource.base import ResourceBase
from viam.resource.registry import Registry, ResourceCreatorRegistration
from viam.resource.types import Model, ModelFamily

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AndroidIMU(MovementSensor):
    """Android IMU movement sensor that pulls data from Pixel 4a Flutter app"""
    
    MODEL: Model = Model(ModelFamily("kilo", "movement_sensor"), "android-imu")
    
    def __init__(self, name: str):
        super().__init__(name)
        self.phone_ip = None
        self.phone_port = 8080
        self.timeout = 5.0
        self.last_reading = None
        self.last_update_time = 0
        
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Dict[str, ResourceBase]) -> "AndroidIMU":
        """Create new Android IMU instance"""
        imu = cls(config.name)
        
        # Get configuration
        attrs = config.attributes.fields
        if "phone_ip" in attrs:
            imu.phone_ip = attrs["phone_ip"].string_value
        if "phone_port" in attrs:
            imu.phone_port = int(attrs["phone_port"].number_value)
        if "timeout" in attrs:
            imu.timeout = float(attrs["timeout"].number_value)
            
        # Auto-discover phone IP if not provided
        if not imu.phone_ip:
            imu.phone_ip = imu._discover_phone_ip()
            
        logger.info(f"Android IMU initialized: {config.name}")
        logger.info(f"Phone endpoint: {imu.phone_ip}:{imu.phone_port}")
        
        return imu
    
    def _discover_phone_ip(self) -> str:
        """Auto-discover Android phone IP on USB tethering network"""
        common_ips = [
            "192.168.42.129",  # Default Android USB tethering
            "192.168.42.1",    # Alternative
            "10.10.10.1",      # Your setup
        ]
        
        for ip in common_ips:
            try:
                response = requests.get(f"http://{ip}:8080/health", timeout=2)
                if response.status_code == 200:
                    logger.info(f"Discovered phone at: {ip}")
                    return ip
            except:
                continue
                
        logger.warning("Could not auto-discover phone IP")
        return None
    
    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Get current IMU readings from Android phone"""
        if not self.phone_ip:
            raise Exception("Phone IP not configured or discovered")
            
        try:
            # Get IMU data from Flutter app
            response = requests.get(
                f"http://{self.phone_ip}:{self.phone_port}/imu",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract IMU values
                readings = {
                    "accelerometer_x": data.get("ax", 0.0),
                    "accelerometer_y": data.get("ay", 0.0),
                    "accelerometer_z": data.get("az", 0.0),
                    "gyroscope_x": data.get("gx", 0.0),
                    "gyroscope_y": data.get("gy", 0.0),
                    "gyroscope_z": data.get("gz", 0.0),
                    "timestamp": data.get("timestamp", time.time())
                }
                
                self.last_reading = readings
                self.last_update_time = time.time()
                
                return readings
            else:
                logger.error(f"Failed to get IMU data: HTTP {response.status_code}")
                if self.last_reading:
                    return self.last_reading
                raise Exception(f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("Timeout getting IMU data from phone")
            if self.last_reading:
                return self.last_reading
            raise Exception("Timeout getting IMU data")
        except Exception as e:
            logger.error(f"Error getting IMU data: {e}")
            if self.last_reading:
                return self.last_reading
            raise
    
    async def get_linear_velocity(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Vector3:
        """Get linear velocity (not implemented for IMU)"""
        return Vector3(x=0.0, y=0.0, z=0.0)
    
    async def get_angular_velocity(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Vector3:
        """Get angular velocity from gyroscope"""
        readings = await self.get_readings(extra, **kwargs)
        return Vector3(
            x=readings.get("gyroscope_x", 0.0),
            y=readings.get("gyroscope_y", 0.0), 
            z=readings.get("gyroscope_z", 0.0)
        )
    
    async def get_linear_acceleration(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Vector3:
        """Get linear acceleration from accelerometer"""
        readings = await self.get_readings(extra, **kwargs)
        return Vector3(
            x=readings.get("accelerometer_x", 0.0),
            y=readings.get("accelerometer_y", 0.0),
            z=readings.get("accelerometer_z", 0.0)
        )
    
    async def get_orientation(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Orientation:
        """Get orientation (not directly available from IMU)"""
        return Orientation(o_x=0.0, o_y=0.0, o_z=0.0, theta=0.0)
    
    async def get_position(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> GeoPoint:
        """Get position (not available from IMU)"""
        return GeoPoint(latitude=0.0, longitude=0.0)
    
    async def get_accuracy(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Tuple[float, float]:
        """Get accuracy (not available from IMU)"""
        return (0.0, 0.0)
    
    async def get_properties(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> MovementSensor.Properties:
        """Get sensor properties"""
        return MovementSensor.Properties(
            linear_acceleration_supported=True,
            angular_velocity_supported=True,
            orientation_supported=False,
            position_supported=False,
            linear_velocity_supported=False,
            compass_heading_supported=False
        )
    
    async def do_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom commands"""
        if command.get("command") == "discover_phone":
            self.phone_ip = self._discover_phone_ip()
            return {"phone_ip": self.phone_ip}
        elif command.get("command") == "get_status":
            return {
                "phone_ip": self.phone_ip,
                "last_update": self.last_update_time,
                "connected": self.phone_ip is not None
            }
        else:
            raise ValueError(f"Unknown command: {command}")

def register():
    """Register the Android IMU module with Viam"""
    logger.info("Registering Android IMU module...")
    
    # Register the Android IMU module with the corrected API reference
    Registry.register_resource_creator(
        MovementSensor.API,  # Fixed: Use API instead of SUBTYPE
        AndroidIMU.MODEL,
        ResourceCreatorRegistration(AndroidIMU.new)
    )
    
    logger.info("Android IMU module registered successfully")

# Main execution
if __name__ == "__main__":
    import sys
    from viam.module.module import Module
    
    async def main():
        # Register the module
        register()
        
        # Create and run module
        module = Module(sys.argv)
        module.add_model_from_registry(MovementSensor.API, AndroidIMU.MODEL)
        await module.start()
    
    asyncio.run(main())