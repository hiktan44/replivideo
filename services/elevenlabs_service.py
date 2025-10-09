"""
ElevenLabs Text-to-Speech Service
Turkish language audio generation
"""

import os
from pathlib import Path
from elevenlabs import AsyncElevenLabs

class ElevenLabsService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        
        if self.api_key:
            self.client = AsyncElevenLabs(api_key=self.api_key)
            self.enabled = True
        else:
            self.enabled = False
        
        self.voice_mapping = {
            "tr_female_professional": "21m00Tcm4TlvDq8ikWAM",
            "tr_male_professional": "JBFqnCBsd6RMkjVDRZzb",
            "tr_female_friendly": "XB0fDUnXU5powFXDhCwa"
        }
    
    async def text_to_speech(self, text: str, voice_type: str) -> str:
        """Convert text to Turkish speech"""
        
        if not self.enabled:
            print("⚠️ ElevenLabs API key not found - using demo mode")
            return await self._create_demo_audio(text)
        
        try:
            voice_id = self.voice_mapping.get(voice_type, self.voice_mapping["tr_female_professional"])
            
            audio_generator = await self.client.text_to_speech.convert(
                text=text[:5000],
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            audio_path = f"videos/audio_{voice_type}.mp3"
            Path("videos").mkdir(exist_ok=True)
            
            with open(audio_path, "wb") as audio_file:
                async for chunk in audio_generator:
                    if chunk:
                        audio_file.write(chunk)
            
            print(f"✅ Audio generated: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ ElevenLabs error: {str(e)}")
            return await self._create_demo_audio(text)
    
    async def _create_demo_audio(self, text: str) -> str:
        """Create demo audio placeholder - valid MP3 file"""
        audio_path = "videos/demo_audio.mp3"
        
        Path("videos").mkdir(exist_ok=True)
        
        mp3_header = bytes([
            0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        
        Path(audio_path).write_bytes(mp3_header)
        
        print(f"📝 Demo audio created: {audio_path}")
        return audio_path
