#!/usr/bin/env python3
"""
Android Face Detection Bridge for Kilo Personality - USB Tethering Edition
Receives face detection events from Pixel 4a and triggers personality responses

Updated for 10.10.10.x USB tethering network
"""
import asyncio
import json
import logging
import socket
import time
from typing import Optional, Dict, Any
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AndroidFaceBridge:
    """Bridge between Android face detection and Kilo personality system (USB Tethering)"""
    
    def __init__(self):
        # USB tethering network configuration
        self.android_host = "10.10.10.1"
        self.android_port = 8080
        self.pi_usb_ip = "10.10.10.67"
        self.personality_socket = "/opt/kilo/personality/kilo.sock"
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Face detection configuration
        self.face_confidence_threshold = 0.7
        self.greeting_cooldown = 30  # seconds
        self.last_greetings = {}  # face_id -> timestamp
        
        # Load people database
        self.people_db = self._load_people_db()
        
        logger.info(f"Android Face Bridge starting (USB Tethering)")
        logger.info(f"Android Host: {self.android_host}")
        logger.info(f"Pi USB IP: {self.pi_usb_ip}")
    
    def _load_people_db(self) -> Dict[str, Any]:
        """Load people.json for face recognition"""
        try:
            with open("/opt/kilo/personality/people.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load people.json: {e}")
            return {}
    
    async def start(self):
        """Start the face detection bridge"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("Starting Android Face Detection Bridge (USB Tethering)...")
        
        # Start face streaming task
        tasks = [
            asyncio.create_task(self._stream_face_events()),
            asyncio.create_task(self._watchdog())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Face bridge error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the face detection bridge"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Face detection bridge stopped")
    
    async def _stream_face_events(self):
        """Connect to Android app and stream face events via HTTP"""
        url = f"http://{self.android_host}:{self.android_port}/faces"
        backoff = 1.0
        max_backoff = 30.0
        
        while self.running:
            try:
                # Connect to face detection endpoint
                async with self.session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        backoff = 1.0  # Reset backoff on success
                        logger.info("Connected to Android face detection stream")
                        
                        # Read face events
                        faces_data = await resp.json()
                        await self._handle_face_event({"faces": faces_data, "timestamp": time.time()})
                        
            except Exception as e:
                logger.warning(f"Face stream connection failed: {e}, retrying in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, max_backoff)
    
    async def _handle_face_event(self, event: Dict[str, Any]):
        """Handle face detection event from Android app"""
        try:
            faces = event.get("faces", [])
            timestamp = event.get("timestamp", time.time())
            
            for face in faces:
                if face.get("confidence", 0) >= self.face_confidence_threshold:
                    await self._process_face_detection(face, timestamp)
                    
        except Exception as e:
            logger.error(f"Error handling face event: {e}")
    
    async def _process_face_detection(self, face: Dict[str, Any], timestamp: float):
        """Process detected face and trigger personality response"""
        face_id = face.get("id", "unknown")
        confidence = face.get("confidence", 0)
        
        # Check greeting cooldown
        last_greeting = self.last_greetings.get(face_id, 0)
        if timestamp - last_greeting < self.greeting_cooldown:
            return
        
        # Update last greeting time
        self.last_greetings[face_id] = timestamp
        
        # Look up person in database
        person = self.people_db.get(face_id, {})
        name = person.get("name", "stranger")
        vehicle = person.get("vehicle", "unknown")
        snark_level = person.get("snark", 2)
        dodge_owner = person.get("dodge_owner", False)
        
        logger.info(f"Face detected: {name} (confidence: {confidence:.2f})")
        
        # Trigger personality greeting
        await self._trigger_greeting(name, vehicle, snark_level, dodge_owner)
    
    async def _trigger_greeting(self, name: str, vehicle: str, snark_level: int, dodge_owner: bool):
        """Send greeting command to personality daemon"""
        try:
            # Connect to personality socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            
            try:
                sock.connect(self.personality_socket)
                
                # Prepare greeting command
                if name == "stranger":
                    command = "greet_newcomer"
                else:
                    # Send person info as JSON data with the command
                    greeting_data = {
                        "command": "greet_regular",
                        "name": name,
                        "vehicle": vehicle,
                        "snark_level": snark_level,
                        "dodge_owner": dodge_owner
                    }
                    command = json.dumps(greeting_data)
                
                # Send command to personality
                sock.send((command + "\n").encode())
                
                # Read response
                response = sock.recv(1024).decode().strip()
                logger.info(f"Personality response: {response}")
                
            finally:
                sock.close()
                
        except Exception as e:
            logger.error(f"Failed to send greeting to personality: {e}")
    
    async def _watchdog(self):
        """Watchdog to monitor connection health"""
        while self.running:
            try:
                # Check Android app connectivity
                async with self.session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.debug("Android face detection app is healthy")
                    else:
                        logger.warning(f"Android app health check failed: {resp.status}")
                        
            except Exception as e:
                logger.warning(f"Android app health check error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds

async def main():
    """Main entry point"""
    bridge = AndroidFaceBridge()
    await bridge.start()

if __name__ == "__main__":
    asyncio.run(main()) < self.greeting_cooldown:
            return
        
        # Update last greeting time
        self.last_greetings[face_id] = timestamp
        
        # Look up person in database
        person = self.people_db.get(face_id, {})
        name = person.get("name", "stranger")
        vehicle = person.get("vehicle", "unknown")
        snark_level = person.get("snark", 2)
        dodge_owner = person.get("dodge_owner", False)
        
        logger.info(f"Face detected: {name} (confidence: {confidence:.2f}) via USB tether")
        
        # Trigger personality greeting
        await self._trigger_greeting(name, vehicle, snark_level, dodge_owner)
    
    async def _trigger_greeting(self, name: str, vehicle: str, snark_level: int, dodge_owner: bool):
        """Send greeting command to personality daemon"""
        try:
            # Connect to personality socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            
            try:
                sock.connect(self.personality_socket)
                
                # Prepare greeting command
                if name == "stranger":
                    command = "greet_newcomer"
                else:
                    # Send person info as JSON data with the command
                    greeting_data = {
                        "command": "greet_regular",
                        "name": name,
                        "vehicle": vehicle,
                        "snark_level": snark_level,
                        "dodge_owner": dodge_owner
                    }
                    command = json.dumps(greeting_data)
                
                # Send command to personality
                sock.send((command + "\n").encode())
                
                # Read response
                response = sock.recv(1024).decode().strip()
                logger.info(f"Personality response: {response}")
                
            finally:
                sock.close()
                
        except Exception as e:
            logger.error(f"Failed to send greeting to personality: {e}")
    
    async def _watchdog(self):
        """Watchdog to monitor connection health"""
        while self.running:
            try:
                # Check Android app connectivity
                async with self.session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.debug("Android face detection app is healthy via USB tether")
                    else:
                        logger.warning(f"Android app health check failed: {resp.status}")
                        
            except Exception as e:
                logger.warning(f"Android app health check error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def test_connectivity(self):
        """Test connectivity to Android app"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    return {
                        "reachable": resp.status == 200,
                        "status_code": resp.status,
                        "android_host": self.android_host,
                        "connection_type": "usb_tether"
                    }
        except Exception as e:
            return {
                "reachable": False,
                "error": str(e),
                "android_host": self.android_host,
                "connection_type": "usb_tether"
            }

async def main():
    """Main entry point"""
    bridge = AndroidFaceBridge()
    await bridge.start()

if __name__ == "__main__":
    asyncio.run(main())
</create_file>