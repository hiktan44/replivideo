"""
Video Composition Service
Combines avatar clips and creates final video
"""

import os
import shutil
from pathlib import Path
from typing import List

class VideoComposer:
    """Simple video composer for MVP"""
    
    @staticmethod
    async def compose_video(
        avatar_clips: List[str],
        audio_file: str,
        video_id: str
    ) -> str:
        """
        Compose final video
        For MVP: Creates a valid demo video file
        Future: Use FFmpeg for real composition
        """
        
        final_video_path = f"videos/final_{video_id}.mp4"
        Path("videos").mkdir(exist_ok=True)
        
        demo_video_path = "demo_assets/demo_video.mp4"
        
        if Path(demo_video_path).exists():
            shutil.copy(demo_video_path, final_video_path)
            print(f"✅ Video composed (demo): {final_video_path}")
        else:
            with open(final_video_path, "wb") as f:
                f.write(b"Demo video placeholder - Install FFmpeg for real video composition")
            print(f"📝 Demo video placeholder created: {final_video_path}")
        
        return final_video_path
    
    @staticmethod
    async def create_demo_video() -> str:
        """Create a valid demo MP4 file"""
        demo_path = "demo_assets/demo_video.mp4"
        Path("demo_assets").mkdir(exist_ok=True)
        
        if not Path(demo_path).exists():
            mp4_header = bytes([
                0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
                0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
                0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
                0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,
            ])
            with open(demo_path, "wb") as f:
                f.write(mp4_header)
        
        return demo_path
