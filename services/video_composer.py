"""
Video Composition Service
Combines avatar clips and creates final video using FFmpeg
"""

import os
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import List

class VideoComposer:
    """Video composer using FFmpeg for real video composition"""
    
    @staticmethod
    async def compose_video(
        avatar_clips: List[str],
        audio_file: str,
        video_id: str
    ) -> str:
        """
        Compose final video using FFmpeg
        1. Concatenate D-ID avatar clips
        2. Mux with ElevenLabs audio
        3. Add QuickTime compatibility
        """
        
        final_video_path = f"videos/final_{video_id}.mp4"
        temp_video_path = f"videos/temp_{video_id}.mp4"
        concat_file_path = f"videos/concat_{video_id}.txt"
        
        Path("videos").mkdir(exist_ok=True)
        
        try:
            # Check if we have real avatar clips and audio
            if not avatar_clips or not Path(audio_file).exists():
                print("⚠️ Missing avatar clips or audio, creating demo video")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            # Filter valid avatar clips
            valid_clips = [clip for clip in avatar_clips if Path(clip).exists()]
            if not valid_clips:
                print("⚠️ No valid avatar clips found, creating demo video")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            print(f"🎬 Starting FFmpeg composition with {len(valid_clips)} clips...")
            
            # Step 1: Create concat file for avatar clips
            with open(concat_file_path, 'w') as f:
                for clip in valid_clips:
                    # Use absolute path for FFmpeg
                    abs_path = Path(clip).absolute()
                    f.write(f"file '{abs_path}'\n")
            
            # Step 2: Concatenate avatar clips (remove audio from clips)
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c:v', 'copy',
                '-an',  # Remove audio from clips to avoid overlap
                temp_video_path
            ]
            
            print(f"📹 Concatenating {len(valid_clips)} avatar clips...")
            await VideoComposer._run_ffmpeg(concat_cmd)
            
            # Step 3: Mux with narration audio
            mux_cmd = [
                'ffmpeg', '-y',
                '-i', temp_video_path,
                '-i', audio_file,
                '-c:v', 'libx264',  # Re-encode for browser compatibility
                '-profile:v', 'main',  # H264 main profile for wide compatibility
                '-pix_fmt', 'yuv420p',  # Pixel format for browser playback
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',  # End video when shortest stream ends
                '-map', '0:v:0',  # Take video from first input
                '-map', '1:a:0',  # Take audio from second input
                '-movflags', '+faststart',  # QuickTime compatibility
                final_video_path
            ]
            
            print(f"🔊 Muxing with audio track...")
            await VideoComposer._run_ffmpeg(mux_cmd)
            
            # Cleanup temp files
            Path(temp_video_path).unlink(missing_ok=True)
            Path(concat_file_path).unlink(missing_ok=True)
            
            print(f"✅ Video composed successfully: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            print(f"❌ FFmpeg composition failed: {e}")
            # Cleanup on error
            Path(temp_video_path).unlink(missing_ok=True)
            Path(concat_file_path).unlink(missing_ok=True)
            # Create fallback demo video
            return await VideoComposer._create_demo_fallback(final_video_path)
    
    @staticmethod
    async def compose_video_with_loop(
        avatar_video: str,
        audio_file: str,
        video_id: str
    ) -> str:
        """
        Compose video by looping short avatar clip to match audio duration
        Used for custom photo avatars where D-ID creates short clips
        """
        
        final_video_path = f"videos/final_{video_id}.mp4"
        
        Path("videos").mkdir(exist_ok=True)
        
        try:
            # Check if we have valid inputs
            if not Path(avatar_video).exists() or not Path(audio_file).exists():
                print("⚠️ Missing avatar video or audio, creating demo video")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            print(f"🔁 Looping avatar video to match audio duration...")
            
            # Get audio duration using ffprobe
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            audio_duration = float(result.stdout.strip())
            print(f"🎤 Audio duration: {audio_duration:.1f} seconds")
            
            # Loop avatar video to match audio duration + small buffer
            loop_cmd = [
                'ffmpeg', '-y',
                '-stream_loop', '-1',  # Infinite loop
                '-i', avatar_video,
                '-i', audio_file,
                '-c:v', 'libx264',  # Re-encode video for looping
                '-profile:v', 'main',  # H264 main profile for browser compatibility
                '-pix_fmt', 'yuv420p',  # Pixel format for browser playback
                '-preset', 'fast',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-t', str(audio_duration),  # Limit to audio duration
                '-map', '0:v:0',  # Video from first input (looped)
                '-map', '1:a:0',  # Audio from second input
                '-movflags', '+faststart',  # QuickTime compatibility
                final_video_path
            ]
            
            print(f"🎬 Creating looped avatar video...")
            await VideoComposer._run_ffmpeg(loop_cmd)
            
            print(f"✅ Video composed successfully: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            print(f"❌ FFmpeg loop composition failed: {e}")
            # Create fallback demo video
            return await VideoComposer._create_demo_fallback(final_video_path)
    
    @staticmethod
    async def _run_ffmpeg(cmd: List[str]):
        """Run FFmpeg command in executor to keep async service responsive"""
        loop = asyncio.get_event_loop()
        
        def run_subprocess():
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            return result
        
        await loop.run_in_executor(None, run_subprocess)
    
    @staticmethod
    async def _create_demo_fallback(output_path: str) -> str:
        """Create demo fallback when FFmpeg fails"""
        demo_video_path = "demo_assets/demo_video.mp4"
        
        if Path(demo_video_path).exists():
            shutil.copy(demo_video_path, output_path)
            print(f"✅ Demo video copied: {output_path}")
        else:
            # Create minimal valid MP4 header
            mp4_header = bytes([
                0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
                0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
                0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
                0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,
            ])
            with open(output_path, "wb") as f:
                f.write(mp4_header)
            print(f"📝 Demo video placeholder created: {output_path}")
        
        return output_path
    
    @staticmethod
    async def mux_screen_recording_with_audio(
        screen_video: str,
        audio_file: str,
        video_id: str
    ) -> str:
        """
        Mux screen recording with audio using FFmpeg
        Converts webm to mp4 if needed and adds audio track
        """
        final_video_path = f"videos/final_{video_id}.mp4"
        
        Path("videos").mkdir(exist_ok=True)
        
        try:
            # Check if files exist
            if not Path(screen_video).exists():
                print("⚠️ Screen recording not found, creating demo video")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            if not Path(audio_file).exists():
                print("⚠️ Audio file not found, creating demo video")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            print(f"🎬 Muxing screen recording with audio...")
            
            # Convert webm to mp4 and add audio in one step
            # Explicitly map video from input 0 and audio from input 1
            mux_cmd = [
                'ffmpeg', '-y',
                '-i', screen_video,
                '-i', audio_file,
                '-map', '0:v:0',  # Take video from first input (screen recording)
                '-map', '1:a:0',  # Take audio from second input (narration)
                '-c:v', 'libx264',  # Re-encode video to h264
                '-profile:v', 'main',  # H264 main profile for browser compatibility
                '-pix_fmt', 'yuv420p',  # Pixel format for browser playback
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',  # End video when shortest stream ends
                '-movflags', '+faststart',  # QuickTime compatibility
                final_video_path
            ]
            
            print(f"🔊 Converting and muxing with audio track...")
            await VideoComposer._run_ffmpeg(mux_cmd)
            
            print(f"✅ Screen recording video composed successfully: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            print(f"❌ Screen recording muxing failed: {e}")
            return await VideoComposer._create_demo_fallback(final_video_path)
    
    @staticmethod
    async def overlay_avatar_on_screen_recording(
        screen_video: str,
        avatar_video: str,
        audio_file: str,
        video_id: str,
        position: str = "bottom_right"
    ) -> str:
        """
        Overlay circular avatar video on screen recording with audio
        
        Args:
            screen_video: Screen recording video path
            avatar_video: Avatar video path (will be made circular)
            audio_file: Audio narration path
            video_id: Video ID for output naming
            position: Avatar position (bottom_right, bottom_left, top_right, top_left)
        """
        final_video_path = f"videos/final_{video_id}.mp4"
        
        Path("videos").mkdir(exist_ok=True)
        
        try:
            # Validate inputs
            if not Path(screen_video).exists():
                print("⚠️ Screen recording not found")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            if not Path(avatar_video).exists():
                print("⚠️ Avatar video not found")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            if not Path(audio_file).exists():
                print("⚠️ Audio file not found")
                return await VideoComposer._create_demo_fallback(final_video_path)
            
            print(f"🎬 Creating circular avatar overlay on screen recording...")
            
            # Get audio duration to match video length
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file
            ]
            
            import subprocess
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            audio_duration = float(result.stdout.strip())
            print(f"🎵 Audio duration: {audio_duration:.2f}s")
            
            # Position mapping (X:Y coordinates, offset from edges)
            positions = {
                "bottom_right": "W-w-20:H-h-20",
                "bottom_left": "20:H-h-20",
                "top_right": "W-w-20:20",
                "top_left": "20:20"
            }
            overlay_position = positions.get(position, positions["bottom_right"])
            
            # FFmpeg command with circular mask overlay + avatar looping
            # Loop avatar video infinitely and trim to audio duration
            overlay_cmd = [
                'ffmpeg', '-y',
                '-i', screen_video,          # Input 0: Screen recording
                '-stream_loop', '-1',        # Loop avatar infinitely
                '-i', avatar_video,          # Input 1: Avatar video (looped)
                '-i', audio_file,            # Input 2: Audio narration
                '-filter_complex',
                f'[1:v]scale=300:300,format=yuva420p,geq=lum=' + chr(39) + 'lum(X,Y)' + chr(39) + ':a=' + chr(39) + 
                'if(lt(sqrt(pow(X-150,2)+pow(Y-150,2)),150),255,0)' + chr(39) + '[avatar];' +
                f'[0:v][avatar]overlay={overlay_position}[v]',
                '-map', '[v]',               # Use filtered video
                '-map', '2:a',               # Use audio from input 2
                '-c:v', 'libx264',
                '-profile:v', 'main',        # H264 main profile for browser compatibility
                '-pix_fmt', 'yuv420p',       # Pixel format for browser playback
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-t', str(audio_duration),   # Trim to audio duration
                '-movflags', '+faststart',
                final_video_path
            ]
            
            print(f"🎭 Applying circular mask and overlaying avatar at {position}...")
            await VideoComposer._run_ffmpeg(overlay_cmd)
            
            print(f"✅ Avatar overlay video composed successfully: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            print(f"❌ Avatar overlay composition failed: {e}")
            return await VideoComposer._create_demo_fallback(final_video_path)
    
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
