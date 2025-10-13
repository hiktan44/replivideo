"""
D-ID Avatar Video Generation Service
Creates talking avatar videos
"""

import os
import httpx
import asyncio
import base64
from pathlib import Path
from typing import Optional

class DIDService:
    def __init__(self):
        self.api_key = os.getenv("DID_API_KEY")
        self.base_url = "https://api.d-id.com"
        
        if self.api_key:
            self.enabled = True
        else:
            self.enabled = False
        
        self.avatar_images = {
            "professional_female": "https://d-id-public-bucket.s3.amazonaws.com/alice.jpg",
            "professional_male": "https://d-id-public-bucket.s3.amazonaws.com/adam.jpg",
            "casual_female": "https://d-id-public-bucket.s3.amazonaws.com/amy.jpg",
            "casual_male": "https://d-id-public-bucket.s3.amazonaws.com/mark.jpg"
        }
    
    async def create_avatar_video(self, text: str, avatar_type: str, custom_image_path: Optional[str] = None, audio_path: Optional[str] = None) -> str:
        """Create avatar video using D-ID API
        
        Args:
            text: Script text for lip-sync (used if audio_path not provided)
            avatar_type: Preset avatar type (ignored if custom_image_path provided)
            custom_image_path: Optional path to custom user photo for personalized avatar
            audio_path: Optional path to pre-generated audio file (bypasses text limit)
        """
        
        if not self.enabled:
            print("⚠️ D-ID API key not found - using demo mode")
            return await self._create_demo_video(text, avatar_type)
        
        try:
            # Prepare avatar source
            if custom_image_path:
                # Convert local image to base64 data URI for D-ID API
                image_path = Path(custom_image_path)
                if image_path.exists():
                    image_data = image_path.read_bytes()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    # Detect MIME type
                    mime_type = "image/jpeg" if custom_image_path.endswith('.jpg') or custom_image_path.endswith('.jpeg') else "image/png"
                    avatar_url = f"data:{mime_type};base64,{base64_image}"
                else:
                    print(f"⚠️ Custom image not found: {custom_image_path}, using default")
                    avatar_url = self.avatar_images.get(avatar_type, self.avatar_images["professional_female"])
            else:
                avatar_url = self.avatar_images.get(avatar_type, self.avatar_images["professional_female"])
            
            headers = {
                "Authorization": f"Basic {self.api_key}",
                "Content-Type": "application/json"
            }
            
            print(f"🔑 D-ID Auth: Basic {self.api_key[:15]}...{self.api_key[-10:]}")
            
            # Use audio file if provided (bypasses text limit)
            if audio_path and Path(audio_path).exists():
                # Get Replit domain for audio URL
                replit_domain = os.getenv("REPLIT_DOMAINS", "").split(",")[0]
                audio_filename = Path(audio_path).name
                audio_url = f"https://{replit_domain}/audio/{audio_filename}"
                
                print(f"🎵 Using audio file: {audio_url}")
                
                payload = {
                    "source_url": avatar_url,
                    "script": {
                        "type": "audio",
                        "audio_url": audio_url
                    },
                    "config": {
                        "fluent": True,
                        "result_format": "mp4"
                    }
                }
            else:
                # Fallback to text (with 750 word limit for 5min video)
                text_limited = " ".join(text.split()[:750])  # ~750 words = 5min
                print(f"📝 Using text (limited to 750 words)")
                
                payload = {
                    "source_url": avatar_url,
                    "script": {
                        "type": "text",
                        "input": text_limited,
                        "provider": {
                            "type": "microsoft",
                            "voice_id": "tr-TR-EmelNeural"
                        }
                    },
                    "config": {
                        "fluent": True,
                        "result_format": "mp4"
                    }
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/talks",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                talk_id = result["id"]
                
                for _ in range(30):
                    await asyncio.sleep(2)
                    
                    status_response = await client.get(
                        f"{self.base_url}/talks/{talk_id}",
                        headers=headers
                    )
                    status_data = status_response.json()
                    
                    if status_data["status"] == "done":
                        video_url = status_data["result_url"]
                        
                        video_response = await client.get(video_url)
                        video_path = f"videos/avatar_{talk_id}.mp4"
                        
                        Path("videos").mkdir(exist_ok=True)
                        Path(video_path).write_bytes(video_response.content)
                        
                        print(f"✅ Avatar video created: {video_path}")
                        return video_path
                    
                    elif status_data["status"] == "error":
                        raise Exception(f"D-ID error: {status_data.get('error')}")
                
                raise Exception("D-ID timeout")
                
        except Exception as e:
            print(f"❌ D-ID error: {str(e)}")
            return await self._create_demo_video(text, avatar_type)
    
    async def _create_demo_video(self, text: str, avatar_type: str) -> str:
        """Return existing demo video or raise error"""
        video_path = f"videos/demo_avatar_{avatar_type}.mp4"
        
        # Check if demo video exists
        if Path(video_path).exists():
            print(f"📝 Using existing demo avatar video: {video_path}")
            return video_path
        else:
            raise Exception(f"Demo video not found: {video_path}. Please create valid demo videos first.")
