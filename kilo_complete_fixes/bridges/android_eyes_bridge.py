#!/usr/bin/env python3
"""
Android Eyes Display Bridge for Kilo Personality
Controls animated eyes on Pixel 4a display based on robot state

Maps personality events to visual eye states and animations
"""
import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AndroidEyesBridge:
    """Bridge between Kilo personality and Android eyes display"""
    
    def __init__(self):
        self.android_host = "192.168.42.129"
        self.android_port = 8080
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Eye state configuration
        self.eye_states = {
            "idle": {"color": "#66a6ff", "intensity": 0.6, "animation": "gentle_blink"},
            "speak": {"color": "#ff6b6b", "intensity": 0.9, "animation": "talk"},
            "focus": {"color": "#4ecdc4", "intensity": 0.8, "animation": "narrow"},
            "worried": {"color": "#ff6b6b", "intensity": 0.4, "animation": "nervous"},
            "happy": {"color": "#66ff66", "intensity": 1.0, "animation": "sparkle"},
            "sleep": {"color": "#6666ff", "intensity": 0.3, "animation": "slow_blink"},
            "charging": {"color": "#ff66ff", "intensity": 0.7, "animation": "pulse"},
            "dreaming": {"color": "#ff66ff", "intensity": 0.5, "animation": "dream"},
        }
        
        # Current state tracking
        self.current_state = "idle"
        self.state_start_time = time.time()
        
    async def start(self):
        """Start the eyes display bridge"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("Starting Android Eyes Display Bridge...")
        
        # Set initial state
        await self.set_eye_state("idle")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_personality_events()),
            asyncio.create_task(self._watchdog())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Eyes bridge error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the eyes bridge"""
        self.running = False
        if self.session:
            await self.session.close()
        
        # Set sleep state before stopping
        await self.set_eye_state("sleep")
        logger.info("Eyes display bridge stopped")
    
    async def set_eye_state(self, state: str, duration_ms: Optional[int] = None, **kwargs):
        """Set eye display state"""
        if state not in self.eye_states:
            logger.warning(f"Unknown eye state: {state}")
            return
        
        try:
            config = self.eye_states[state].copy()
            config.update(kwargs)  # Allow override of defaults
            
            if duration_ms:
                config["duration_ms"] = duration_ms
            
            # Send to Android eyes display
            url = f"http://{self.android_host}:{self.android_port}/eyes/set"
            
            payload = {
                "state": state,
                **config
            }
            
            async with self.session.post(url, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    self.current_state = state
                    self.state_start_time = time.time()
                    logger.info(f"Eyes set to: {state}")
                else:
                    logger.warning(f"Failed to set eye state: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Error setting eye state: {e}")
    
    async def _monitor_personality_events(self):
        """Monitor personality daemon for eye state changes"""
        personality_socket = "/opt/kilo/personality/kilo.sock"
        
        while self.running:
            try:
                # Connect to personality socket
                import socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                
                try:
                    sock.connect(personality_socket)
                    
                    while self.running:
                        # Read commands from personality
                        data = sock.recv(1024).decode().strip()
                        if not data:
                            break
                        
                        await self._handle_personality_command(data)
                        
                finally:
                    sock.close()
                    
                # Brief pause before reconnecting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring personality: {e}")
                await asyncio.sleep(2)
    
    async def _handle_personality_command(self, command: str):
        """Handle personality command and update eyes accordingly"""
        try:
            # Parse command (could be JSON or simple string)
            try:
                cmd_data = json.loads(command)
                cmd_type = cmd_data.get("command", command)
            except:
                cmd_type = command
            
            # Map personality commands to eye states
            eye_mapping = {
                "boot": "idle",
                "demo": "happy",
                "sleep": "sleep",
                "wake": "idle",
                "joke": "speak",
                "scan": "focus",
                "greeting": "happy",
                "greet_newcomer": "speak",
                "greet_regular": "happy",
                "low_battery": "worried",
                "critical_battery": "worried",
                "near_roll": "worried",
                "rollover": "worried",
                "estop_engaged": "worried",
                "estop_released": "focus",
                "dock_start": "focus",
                "dock_success": "happy",
                "charging": "charging",
                "dream": "dreaming"
            }
            
            # Get eye state for command
            eye_state = eye_mapping.get(cmd_type, self.current_state)
            
            # Special handling for speak state
            if cmd_type in ["joke", "greet_newcomer"] or "speak" in cmd_type:
                await self.set_eye_state("speak", duration_ms=3000)
                # Return to previous state after speaking
                await asyncio.sleep(3.5)
                await self.set_eye_state("idle")
            else:
                await self.set_eye_state(eye_state)
                
        except Exception as e:
            logger.error(f"Error handling personality command: {e}")
    
    async def play_emotion_sequence(self, emotions: list):
        """Play a sequence of emotions"""
        for emotion in emotions:
            if not self.running:
                break
            await self.set_eye_state(emotion["state"], emotion.get("duration_ms", 1000))
            await asyncio.sleep(emotion.get("duration_ms", 1000) / 1000.0)
    
    async def _watchdog(self):
        """Watchdog to monitor Android eyes service"""
        while self.running:
            try:
                # Check Android eyes service health
                async with self.session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.debug("Android eyes service is healthy")
                    else:
                        logger.warning(f"Android eyes health check failed: {resp.status}")
                        
            except Exception as e:
                logger.warning(f"Android eyes health check error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds

# Example usage and helper functions
async def test_eye_states():
    """Test all eye states"""
    bridge = AndroidEyesBridge()
    bridge.session = aiohttp.ClientSession()
    
    states = ["idle", "speak", "focus", "worried", "happy", "sleep", "charging"]
    
    for state in states:
        await bridge.set_eye_state(state, duration_ms=2000)
        await asyncio.sleep(2.5)
    
    await bridge.session.close()

async def main():
    """Main entry point"""
    bridge = AndroidEyesBridge()
    await bridge.start()

if __name__ == "__main__":
    asyncio.run(main())
</create_file>