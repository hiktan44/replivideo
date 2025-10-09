"""
HeyGen Avatar Video Generation Service
Creates talking avatar videos with HeyGen API v2
"""

import os
import httpx
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, List

class HeyGenService:
    def __init__(self):
        self.api_key = os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com"  # Use v1 and v2 mixed API
        
        if self.api_key:
            self.enabled = True
        else:
            self.enabled = False
        
        # HeyGen avatar IDs - using their public avatars
        self.avatars = {
            "professional_female": "Daisy-inskirt-20220818",
            "professional_male": "Josh_lite3_20230714",
            "casual_female": "Anna_public_3_20240108",
            "casual_male": "Lucas_public_2_20240210"
        }
        
        # Default Turkish voice ID (will be dynamically fetched)
        self.turkish_voice_id = None
        self.voices_cache = None
    
    async def get_turkish_voices(self) -> List[Dict]:
        """Fetch available Turkish voices from HeyGen API"""
        if self.voices_cache:
            return self.voices_cache
        
        if not self.enabled:
            return []
        
        try:
            headers = {
                "Accept": "application/json",
                "X-Api-Key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v2/voices",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                # Filter Turkish voices (check both language and locale)
                all_voices = data.get("data", {}).get("voices", [])
                turkish_voices = [
                    voice for voice in all_voices
                    if "tr" in voice.get("language", "").lower() or 
                       "tr" in voice.get("locale", "").lower() or
                       "turkish" in voice.get("language", "").lower()
                ]
                
                self.voices_cache = turkish_voices
                
                # Set default Turkish voice if found
                if turkish_voices:
                    # Prefer female professional voice for consistency with D-ID
                    female_voices = [v for v in turkish_voices if v.get("gender") == "female"]
                    if female_voices:
                        self.turkish_voice_id = female_voices[0]["voice_id"]
                    else:
                        self.turkish_voice_id = turkish_voices[0]["voice_id"]
                    
                    print(f"✅ Found {len(turkish_voices)} Turkish voices")
                    print(f"   Selected voice: {next((v['name'] for v in turkish_voices if v['voice_id'] == self.turkish_voice_id), 'Unknown')}")
                
                return turkish_voices
                
        except Exception as e:
            print(f"❌ Error fetching voices: {str(e)}")
            return []
    
    async def create_avatar_video(self, text: str, avatar_type: str, voice_type: Optional[str] = None) -> str:
        """Create avatar video using HeyGen API v2"""
        
        if not self.enabled:
            print("⚠️ HeyGen API key not found - using demo mode")
            return await self._create_demo_video(text, avatar_type)
        
        try:
            # Get Turkish voice if not already fetched
            if not self.turkish_voice_id:
                await self.get_turkish_voices()
            
            # Use default voice if still not found
            if not self.turkish_voice_id:
                print("⚠️ No Turkish voice found, using demo mode")
                return await self._create_demo_video(text, avatar_type)
            
            # Get avatar ID
            avatar_id = self.avatars.get(avatar_type, self.avatars["professional_female"])
            
            # Truncate text to 1500 characters (HeyGen limit)
            truncated_text = text[:1500]
            
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Create video generation request (HeyGen v2 API format)
            payload = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id
                    },
                    "voice": {
                        "type": "text",
                        "input_text": truncated_text,
                        "voice_id": self.turkish_voice_id
                    },
                    "background": {
                        "type": "color",
                        "value": "#FFFFFF"
                    }
                }],
                "dimension": {
                    "width": 1280,
                    "height": 720
                },
                "test": False
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Generate video
                print(f"📤 Sending video generation request to HeyGen...")
                response = await client.post(
                    f"{self.base_url}/v2/video/generate",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("error"):
                    raise Exception(f"HeyGen API error: {result['error']}")
                
                video_id = result.get("data", {}).get("video_id")
                if not video_id:
                    raise Exception("No video_id received from HeyGen")
                
                print(f"📝 Video generation started with ID: {video_id}")
                
                # Poll for video status
                max_attempts = 60  # 2 minutes max wait
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                    
                    status_response = await client.get(
                        f"{self.base_url}/v1/video_status.get",
                        headers=headers,
                        params={"video_id": video_id}
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    # V1 API returns code 100 for success
                    if status_data.get("code") != 100:
                        raise Exception(f"Status check error: {status_data.get('message', 'Unknown error')}")
                    
                    video_status = status_data.get("data", {}).get("status")
                    
                    if video_status == "completed":
                        video_url = status_data.get("data", {}).get("video_url")
                        
                        if not video_url:
                            raise Exception("No video URL in completed status")
                        
                        # Download the video
                        print(f"📥 Downloading video from HeyGen...")
                        video_response = await client.get(video_url)
                        video_response.raise_for_status()
                        
                        # Save video locally
                        video_path = f"videos/heygen_{video_id}.mp4"
                        Path("videos").mkdir(exist_ok=True)
                        Path(video_path).write_bytes(video_response.content)
                        
                        print(f"✅ HeyGen avatar video created: {video_path}")
                        return video_path
                    
                    elif video_status == "processing":
                        if attempt % 5 == 0:  # Print status every 10 seconds
                            print(f"⏳ Video still processing... ({attempt * 2}s elapsed)")
                    
                    elif video_status in ["failed", "error"]:
                        error_msg = status_data.get("data", {}).get("error", {}).get("message", "Unknown error")
                        raise Exception(f"Video generation failed: {error_msg}")
                
                raise Exception("Video generation timeout after 2 minutes")
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HeyGen HTTP error {e.response.status_code}: {e.response.text}")
            return await self._create_demo_video(text, avatar_type)
        except Exception as e:
            print(f"❌ HeyGen error: {str(e)}")
            return await self._create_demo_video(text, avatar_type)
    
    async def _create_demo_video(self, text: str, avatar_type: str) -> str:
        """Create demo video placeholder when API is unavailable"""
        video_path = f"videos/demo_heygen_{avatar_type}.mp4"
        
        Path("videos").mkdir(exist_ok=True)
        
        # Copy the actual demo video file
        demo_source = Path("demo_assets/demo_video.mp4")
        if demo_source.exists():
            # Use the real demo video
            import shutil
            shutil.copy(demo_source, video_path)
        else:
            # Fallback: create a simple valid MP4
            import subprocess
            subprocess.run([
                "ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=5",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", "5", "-c:v", "libx264", "-c:a", "aac", 
                "-movflags", "+faststart", video_path, "-y"
            ], capture_output=True, check=False)
        
        print(f"📝 Demo HeyGen video created: {video_path}")
        return video_path
    
    async def get_video_status(self, video_id: str) -> Dict:
        """Check the status of a video generation job"""
        if not self.enabled:
            return {"status": "demo", "message": "Demo mode"}
        
        try:
            headers = {
                "X-Api-Key": self.api_key,
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/video_status.get",
                    headers=headers,
                    params={"video_id": video_id}
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"❌ Error checking video status: {str(e)}")
            return {"status": "error", "message": str(e)}