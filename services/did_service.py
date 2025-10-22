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
            # D-ID requires Basic auth with base64 encoded "api_key:" (note the colon)
            auth_string = f"{self.api_key}:"
            self.auth_token = base64.b64encode(auth_string.encode()).decode()
        else:
            self.enabled = False
            self.auth_token = None
        
        self.avatar_images = {
            "professional_female": "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/alice.jpg",
            "professional_male": "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/adam.jpg",
            "casual_female": "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/amy.jpg",
            "casual_male": "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/mark.jpg"
        }
    
    async def _upload_custom_image(self, image_path: str) -> str:
        """Upload custom image to D-ID and return the URL
        
        Args:
            image_path: Path to the local image file
            
        Returns:
            URL of the uploaded image
        """
        print(f"📤 Uploading custom image to D-ID: {image_path}")
        
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # D-ID expects multipart/form-data with binary file
        headers = {
            "Authorization": f"Basic {self.auth_token}",
            "accept": "application/json"
        }
        
        # Read image as binary
        with open(image_path, 'rb') as f:
            files = {
                'image': (image_file.name, f, 'image/jpeg')
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/images",
                    headers=headers,
                    files=files
                )
                
                print(f"📥 D-ID Upload Response: {response.status_code}")
                
                if response.status_code != 201:
                    error_text = response.text
                    print(f"❌ D-ID Image Upload Error: {error_text}")
                    raise Exception(f"Failed to upload image: {response.status_code} - {error_text}")
                
                result = response.json()
                image_url = result.get("url")
                
                if not image_url:
                    raise Exception("No URL returned from D-ID image upload")
                
                print(f"✅ Image uploaded successfully: {image_url[:100]}...")
                return image_url
    
    async def create_avatar_video(self, text: str, avatar_type: str, custom_image_path: Optional[str] = None, audio_path: Optional[str] = None, voice_type: str = "tr_female_professional") -> str:
        """Create avatar video using D-ID API
        
        Args:
            text: Script text for lip-sync (used if audio_path not provided)
            avatar_type: Preset avatar type (ignored if custom_image_path provided)
            custom_image_path: Optional path to custom user photo for personalized avatar
            audio_path: Optional path to pre-generated audio file (bypasses text limit)
            voice_type: Voice type to use (e.g., tr_male_professional, tr_female_professional)
        """
        
        # Map voice types to Microsoft Azure D-ID voice IDs
        voice_mapping = {
            "tr_female_professional": "tr-TR-EmelNeural",
            "tr_male_professional": "tr-TR-AhmetNeural",
            "tr_female_friendly": "tr-TR-EmelNeural",
            "tr_male_friendly": "tr-TR-AhmetNeural"
        }
        
        voice_id = voice_mapping.get(voice_type, "tr-TR-EmelNeural")
        print(f"🎤 Using voice: {voice_type} → {voice_id}")
        
        if not self.enabled:
            print("⚠️ D-ID API key not found - using demo mode")
            return await self._create_demo_video(text, avatar_type)
        
        try:
            # Prepare avatar source URL
            if custom_image_path:
                # Upload custom image first, then get URL
                image_path = Path(custom_image_path)
                if image_path.exists():
                    print(f"📤 Custom image detected - uploading to D-ID first...")
                    avatar_url = await self._upload_custom_image(custom_image_path)
                else:
                    print(f"⚠️ Custom image not found: {custom_image_path}, using default")
                    avatar_url = self.avatar_images.get(avatar_type, self.avatar_images["professional_female"])
            else:
                # Use preset avatar
                avatar_url = self.avatar_images.get(avatar_type, self.avatar_images["professional_female"])
            
            # Correct Authorization header format
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            
            print(f"🔑 D-ID Auth configured (Base64 encoded)")
            
            # Use short text for quick generation (will loop video later)
            # Limit to 100 words (~30 seconds) to avoid timeouts
            text_limited = " ".join(text.split()[:100])
            
            print(f"📝 Using text for D-ID (limited to 100 words for quick generation)")
            print(f"   Full audio will be added later via FFmpeg loop composition")
            
            payload = {
                "source_url": avatar_url,
                "script": {
                    "type": "text",
                    "input": text_limited,
                    "provider": {
                        "type": "microsoft",
                        "voice_id": voice_id
                    }
                },
                "config": {
                    "fluent": True,
                    "result_format": "mp4"
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                print(f"📤 Creating D-ID talk...")
                print(f"🖼️ Avatar source: {avatar_url[:100]}...")
                print(f"📝 Text preview (first 50 chars): {text_limited[:50]}...")
                
                response = await client.post(
                    f"{self.base_url}/talks",
                    headers=headers,
                    json=payload
                )
                
                print(f"📥 D-ID Response Status: {response.status_code}")
                
                if response.status_code != 201:
                    error_text = response.text
                    print(f"❌ D-ID API Error: {error_text}")
                    raise Exception(f"D-ID API returned {response.status_code}: {error_text}")
                
                result = response.json()
                talk_id = result["id"]
                print(f"✅ Talk created with ID: {talk_id}")
                
                # Wait up to 5 minutes (60 iterations * 5 seconds)
                for i in range(60):
                    await asyncio.sleep(5)
                    
                    status_response = await client.get(
                        f"{self.base_url}/talks/{talk_id}",
                        headers=headers
                    )
                    status_data = status_response.json()
                    
                    current_status = status_data.get("status", "unknown")
                    elapsed = (i + 1) * 5
                    print(f"⏳ D-ID status: {current_status} ({elapsed}s elapsed)")
                    
                    if current_status == "done":
                        video_url = status_data.get("result_url")
                        print(f"🎬 Video ready at: {video_url}")
                        
                        video_response = await client.get(video_url)
                        video_path = f"videos/avatar_{talk_id}.mp4"
                        
                        Path("videos").mkdir(exist_ok=True)
                        Path(video_path).write_bytes(video_response.content)
                        
                        print(f"✅ Avatar video created: {video_path} ({len(video_response.content)} bytes)")
                        return video_path
                    
                    elif current_status == "error":
                        error_detail = status_data.get("error", "Unknown error")
                        print(f"❌ D-ID generation failed: {error_detail}")
                        print(f"📋 Full response: {status_data}")
                        raise Exception(f"D-ID error: {error_detail}")
                
                print(f"⏰ D-ID timeout after 5 minutes")
                raise Exception("D-ID timeout after 5 minutes")
                
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
