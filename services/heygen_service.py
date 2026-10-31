"""
HeyGen Avatar Video Generation Service
Creates talking avatar videos with HeyGen API v3
"""

import os
import httpx
import asyncio
import re
from urllib.parse import quote
from uuid import uuid4
from pathlib import Path
from typing import Optional, Dict, List

class HeyGenService:
    def __init__(self):
        self.api_key = os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com"
        
        if self.api_key:
            self.enabled = True
        else:
            self.enabled = False
        
        # HeyGen avatar IDs - using their public avatars (Updated Oct 2025)
        self.avatars = {
            "professional_female": "Daisy-inskirt-20220818",
            "professional_male": "Adrian_public_2_20240312",  # Adrian in Blue Suit
            "casual_female": "Anna_public_3_20240108",
            "casual_male": "Adrian_public_20240312"  # Adrian in Blue Sweater
        }
        
        # Default Turkish voice ID (will be dynamically fetched)
        self.turkish_voice_id = None
        self.voices_cache = None
    
    async def get_turkish_voices(self) -> List[Dict]:
        """Fetch available Turkish voices from HeyGen API"""
        if self.voices_cache is not None:
            return self.voices_cache
        
        if not self.enabled:
            return []
        
        try:
            headers = {
                "Accept": "application/json",
                "X-Api-Key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                turkish_voices = []
                params = {"language": "Turkish", "limit": 100}
                seen_tokens = set()
                for _ in range(100):
                    response = await client.get(
                        f"{self.base_url}/v3/voices", headers=headers, params=params
                    )
                    response.raise_for_status()
                    data = response.json()
                    voices = data.get("data")
                    if not isinstance(voices, list):
                        raise ValueError("Unexpected v3 voice list response")
                    turkish_voices.extend(
                        voice for voice in voices
                        if voice.get("voice_id") and
                        str(voice.get("language") or "").lower() in
                        {"turkish", "turkey", "tr-tr", "tr"}
                    )
                    if not data.get("has_more"):
                        break
                    token = data.get("next_token")
                    if not token or token in seen_tokens:
                        raise ValueError("Invalid v3 voice pagination cursor")
                    seen_tokens.add(token)
                    params["token"] = token
                else:
                    raise ValueError("v3 voice pagination limit exceeded")

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
        """Create avatar video using HeyGen API v3"""
        
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
            
            # Pin the former Studio renderer: v3 defaults to Avatar IV when
            # engine is omitted. Keep the existing 720p landscape composition.
            payload = {
                "type": "avatar",
                "avatar_id": avatar_id,
                "script": truncated_text,
                "voice_id": self.turkish_voice_id,
                "background": {"type": "color", "value": "#FFFFFF"},
                "aspect_ratio": "16:9",
                "resolution": "720p",
                "engine": {"type": "avatar_iii"},
            }
            headers["Idempotency-Key"] = str(uuid4())

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Generate video
                print(f"📤 Sending video generation request to HeyGen...")
                response = await client.post(
                    f"{self.base_url}/v3/videos",
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
                max_attempts = 300  # 10 minutes max wait (300 * 2 seconds)
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                    
                    status_response = await client.get(
                        f"{self.base_url}/v3/videos/{quote(video_id, safe='')}",
                        headers={"X-Api-Key": self.api_key, "Accept": "application/json"}
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    # v3 wraps the result in data; it has no legacy code=100.
                    if status_data.get("error"):
                        raise RuntimeError("HeyGen status check failed")
                    detail = status_data.get("data", {})
                    video_status = detail.get("status")

                    if video_status == "completed":
                        video_url = detail.get("video_url")
                        
                        if not video_url:
                            raise Exception("No video URL in completed status")
                        
                        # Download the video
                        print(f"📥 Downloading video from HeyGen...")
                        video_response = await client.get(video_url)
                        video_response.raise_for_status()
                        
                        # Save video locally
                        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", video_id)[:160]
                        video_path = f"videos/heygen_{safe_id}.mp4"
                        Path("videos").mkdir(exist_ok=True)
                        Path(video_path).write_bytes(video_response.content)
                        
                        print(f"✅ HeyGen avatar video created: {video_path}")
                        return video_path
                    
                    elif video_status in ["processing", "waiting"]:
                        if attempt % 5 == 0:  # Print status every 10 seconds
                            status_text = "queued, waiting to process" if video_status == "waiting" else "processing"
                            print(f"⏳ Video {status_text}... ({attempt * 2}s elapsed)")
                    
                    elif video_status in ["failed", "error"]:
                        error_msg = detail.get("failure_message") or detail.get("failure_code") or "Unknown error"
                        raise Exception(f"Video generation failed: {error_msg}")
                    
                    elif video_status not in ["processing", "pending", "waiting"]:
                        # Unknown status
                        print(f"⚠️ Unknown video status: {video_status}")
                
                raise Exception("Video generation timeout after 10 minutes")
                
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
                    f"{self.base_url}/v3/videos/{quote(video_id, safe='')}",
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"❌ Error checking video status: {str(e)}")
            return {"status": "error", "message": str(e)}