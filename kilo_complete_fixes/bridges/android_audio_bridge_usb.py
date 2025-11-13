#!/usr/bin/env python3
"""
Android Audio Bridge for Kilo Personality - USB Tethering Edition
Routes audio between Pi and Pixel 4a:
- Pi TTS (kilosay) → Phone speaker
- Phone microphone → Pi ASR (optional)
- Engine rev sounds → Phone audio

Updated for 10.10.10.x USB tethering network
"""
import asyncio
import json
import logging
import subprocess
import wave
import tempfile
import os
from typing import Optional, Dict, Any
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AndroidAudioBridge:
    """Bridge between Pi audio and Android audio system (USB Tethering)"""
    
    def __init__(self):
        # USB tethering network configuration
        self.android_host = "10.10.10.1"
        self.android_port = 8080
        self.pi_usb_ip = "10.10.10.67"
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Audio configuration
        self.sample_rate = 16000
        self.channels = 1
        self.bit_depth = 16
        
        logger.info(f"Android Audio Bridge starting (USB Tethering)")
        logger.info(f"Android Host: {self.android_host}")
        logger.info(f"Pi USB IP: {self.pi_usb_ip}")
        
    async def start(self):
        """Start the audio bridge"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("Starting Android Audio Bridge (USB Tethering)...")
        
        # Create FIFO for audio input from kilosay
        self.audio_fifo = "/tmp/kilo_android_audio.fifo"
        await self._create_audio_fifo()
        
        # Start audio processing tasks
        tasks = [
            asyncio.create_task(self._monitor_tts_output()),
            asyncio.create_task(self._watchdog())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Audio bridge error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the audio bridge"""
        self.running = False
        if self.session:
            await self.session.close()
        
        # Clean up FIFO
        if os.path.exists(self.audio_fifo):
            os.unlink(self.audio_fifo)
        
        logger.info("Audio bridge stopped")
    
    async def _create_audio_fifo(self):
        """Create FIFO for audio communication"""
        try:
            # Remove existing FIFO
            if os.path.exists(self.audio_fifo):
                os.unlink(self.audio_fifo)
            
            # Create new FIFO
            os.mkfifo(self.audio_fifo)
            logger.info(f"Created audio FIFO: {self.audio_fifo}")
            
        except Exception as e:
            logger.error(f"Failed to create audio FIFO: {e}")
    
    async def _monitor_tts_output(self):
        """Monitor TTS output and forward to Android speaker"""
        while self.running:
            try:
                # Read audio data from FIFO (from kilosay)
                with open(self.audio_fifo, 'rb') as fifo:
                    while self.running:
                        data = fifo.read(1024)  # Read in chunks
                        if not data:
                            break
                        
                        # Forward to Android speaker
                        await self._send_to_android_speaker(data)
                        
            except Exception as e:
                logger.error(f"Error monitoring TTS output: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _send_to_android_speaker(self, audio_data: bytes):
        """Send audio data to Android speaker"""
        try:
            # Option 1: HTTP POST with audio data
            url = f"http://{self.android_host}:{self.android_port}/speaker/play"
            
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field('audio', audio_data, 
                          filename='audio.wav', 
                          content_type='audio/wav')
            
            async with self.session.post(url, data=data, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to send audio to Android: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Error sending audio to Android: {e}")
    
    async def speak_text(self, text: str, voice: str = "default"):
        """Send text to Android for TTS processing"""
        try:
            url = f"http://{self.android_host}:{self.android_port}/speaker/tts"
            
            payload = {
                "text": text,
                "voice": voice,
                "sample_rate": self.sample_rate
            }
            
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    logger.info(f"Text sent to Android TTS: {text}")
                else:
                    logger.warning(f"Android TTS failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Error sending text to Android TTS: {e}")
    
    async def play_engine_sound(self, sound_type: str):
        """Play engine rev sound on Android speaker"""
        try:
            url = f"http://{self.android_host}:{self.android_port}/speaker/engine"
            
            payload = {
                "sound": sound_type,  # rev_startup, rev_happy, rev_warning, etc.
                "volume": 0.8
            }
            
            async with self.session.post(url, json=payload, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning(f"Engine sound failed: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Error playing engine sound: {e}")
    
    async def _watchdog(self):
        """Watchdog to monitor Android audio service"""
        while self.running:
            try:
                # Check Android audio service health
                async with self.session.get(f"http://{self.android_host}:{self.android_port}/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.debug("Android audio service is healthy")
                    else:
                        logger.warning(f"Android audio health check failed: {resp.status}")
                        
            except Exception as e:
                logger.warning(f"Android audio health check error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds

class EnhancedKiloSay:
    """Enhanced kilosay that can route to Android speaker (USB Tethering)"""
    
    def __init__(self, android_bridge: AndroidAudioBridge):
        self.android_bridge = android_bridge
        self.use_android = True
        
    async def say(self, text: str, voice: str = "default"):
        """Speak text using Android if available, fallback to local TTS"""
        if self.use_android:
            try:
                await self.android_bridge.speak_text(text, voice)
                return True
            except Exception:
                logger.warning("Android TTS failed, falling back to local")
                self.use_android = False
        
        # Fallback to local TTS
        try:
            # Use existing kilosay binary
            result = subprocess.run(['/usr/local/bin/kilosay', text], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Local TTS failed: {e}")
            return False

async def main():
    """Main entry point"""
    bridge = AndroidAudioBridge()
    
    # Create enhanced kilosay interface
    enhanced_kilosay = EnhancedKiloSay(bridge)
    
    # Example usage
    await enhanced_kilosay.say("Hello from the enhanced USB audio system!")
    await bridge.play_engine_sound("rev_startup")
    
    # Start the bridge
    await bridge.start()

if __name__ == "__main__":
    asyncio.run(main())