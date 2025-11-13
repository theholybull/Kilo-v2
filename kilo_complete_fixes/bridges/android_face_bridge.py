#!/usr/bin/env python3
"""
Android Face Detection Bridge for Kilo Personality
Receives face detection events from Pixel 4a and triggers personality responses

Integrates with Kilo's personality system for personalized greetings
"""
import asyncio
import json
import logging
import socket
from typing import Optional, Dict, Any
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AndroidFaceBridge:
    """Bridge between Android face detection and Kilo personality system"""
    
    def __init__(self):
        self.android_host = "192.168.42.129"
        self.android_port = 8080
        self.personality_socket = "/opt/kilo/personality/kilo.sock"
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Face detection configuration
        self.face_confidence_threshold = 0.7
        self.greeting_cooldown = 30  # seconds
        self.last_greetings = {}  # face_id -> timestamp
        
        # Load people database
        self.people_db = self._load_people_db()
    
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
        
        logger.info("Starting Android Face Detection Bridge...")
        
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
        """Connect to Android app and stream face events"""
        url = f"http://{self.android_host}:{self.android_port}/faces"
        backoff = 1.0
        max_backoff = 30.0
        
        while self.running:
            try:
                # Connect to face detection stream
                async with self.session.ws_connect(url) as ws:
                    backoff = 1.0  # Reset backoff on success
                    logger.info("Connected to Android face detection stream")
                    
                    async for msg in ws:
                        if not self.running:
                            break
                            
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_face_event(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                            
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
            return  # Skip if greeted recently
        
        # Check if this is a known person
        person_info = self.people_db.get(face_id, {})
        name = person_info.get("name", None)
        
        if name:
            # Known person - trigger regular greeting
            await self._send_personality_command("greet_regular", {
                "name": name,
                "face_id": face_id,
                "confidence": confidence
            })
            logger.info(f"Greeted known person: {name} (face_id: {face_id})")
        else:
            # Unknown person - trigger newcomer greeting
            await self._send_personality_command("greet_newcomer", {
                "face_id": face_id,
                "confidence": confidence
            })
            logger.info(f"Greeted newcomer (face_id: {face_id})")
        
        # Update last greeting time
        self.last_greetings[face_id] = timestamp
    
    async def _send_personality_command(self, command: str, params: Dict[str, Any] = None):
        """Send command to Kilo personality daemon via UNIX socket"""
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            
            try:
                sock.connect(self.personality_socket)
                
                # Send command
                cmd_data = {
                    "cmd": command,
                    "params": params or {}
                }
                
                message = json.dumps(cmd_data) + "\n"
                sock.sendall(message.encode())
                
                # Read response (optional)
                response = sock.recv(1024).decode().strip()
                logger.debug(f"Personality response: {response}")
                
            finally:
                sock.close()
                
        except Exception as e:
            logger.warning(f"Failed to send command to personality: {e}")
    
    async def _watchdog(self):
        """Watchdog to monitor connection health"""
        while self.running:
            try:
                # Check if Android app is reachable
                async with self.session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning("Android app health check failed")
                
            except Exception as e:
                logger.warning(f"Health check failed: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds

# Standalone execution
async def main():
    bridge = AndroidFaceBridge()
    await bridge.start()

if __name__ == "__main__":
    import time
    asyncio.run(main())
</create_file>