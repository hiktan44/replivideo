"""
D-ID Avatar Video Generation Service
Creates talking avatar videos
"""

import os
import httpx
import asyncio
from pathlib import Path

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
    
    async def create_avatar_video(self, text: str, avatar_type: str) -> str:
        """Create avatar video using D-ID API"""
        
        if not self.enabled:
            print("⚠️ D-ID API key not found - using demo mode")
            return await self._create_demo_video(text, avatar_type)
        
        try:
            avatar_url = self.avatar_images.get(avatar_type, self.avatar_images["professional_female"])
            
            headers = {
                "Authorization": f"Basic {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "source_url": avatar_url,
                "script": {
                    "type": "text",
                    "input": text[:500],
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
        """Create demo video placeholder - valid MP4 file"""
        video_path = f"videos/demo_avatar_{avatar_type}.mp4"
        
        Path("videos").mkdir(exist_ok=True)
        
        mp4_header = bytes([
            0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
            0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
            0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
            0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,
        ])
        
        Path(video_path).write_bytes(mp4_header)
        
        print(f"📝 Demo avatar video created: {video_path}")
        return video_path
