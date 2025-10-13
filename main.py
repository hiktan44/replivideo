"""
AI Avatar Video Maker - Replit Complete Application
Generates 10-minute Turkish tutorial videos from GitHub repositories
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, model_validator
from typing import Optional, Dict, List
import os
import uuid
import json
import asyncio
from datetime import datetime
import httpx
import base64
from pathlib import Path
import shutil
from PIL import Image
import io
from services.document_analyzer import DocumentAnalyzer

app = FastAPI(title="AI Avatar Video Maker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent video database
VIDEO_DB_FILE = Path("videos_db.json")
db_lock = asyncio.Lock()  # Thread safety for videos_db access

def load_videos_db() -> Dict:
    """Load video database from JSON file"""
    if VIDEO_DB_FILE.exists():
        try:
            with open(VIDEO_DB_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Error loading videos database: {str(e)}")
            return {}
    return {}

async def save_videos_db(db: Dict):
    """Save video database to JSON file with thread safety"""
    async with db_lock:
        with open(VIDEO_DB_FILE, "w") as f:
            json.dump(db, f, indent=2)

# Load existing videos on startup
videos_db = load_videos_db()

class VideoCreateRequest(BaseModel):
    url: Optional[HttpUrl] = None
    document_id: Optional[str] = None
    avatar_type: str = "professional_female"
    voice_type: str = "tr_female_professional"
    video_style: str = "tutorial"
    provider: str = "heygen"  # "did" or "heygen"
    video_duration: int = 10  # 5, 10, or 15 minutes
    mode: str = "avatar"  # "avatar", "screen_recording", or "custom_avatar_overlay"
    scroll_speed: str = "medium"  # For screen recording: "slow", "medium", "fast"
    custom_prompt: Optional[str] = None
    custom_avatar_image_id: Optional[str] = None  # For custom_avatar_overlay mode
    
    @model_validator(mode='after')
    def validate_source(self):
        if not self.url and not self.document_id:
            raise ValueError("Either url or document_id must be provided")
        if self.url and self.document_id:
            raise ValueError("Cannot provide both url and document_id")
        
        # Custom avatar images only work with D-ID provider
        if hasattr(self, 'custom_avatar_image_id') and self.custom_avatar_image_id and hasattr(self, 'provider') and self.provider != "did":
            raise ValueError("Custom avatar images require D-ID provider. Please select 'did' as provider.")
        
        return self

class VideoStatusResponse(BaseModel):
    video_id: str
    status: str
    progress: int
    current_stage: str
    video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

class ScriptPreviewRequest(BaseModel):
    url: Optional[HttpUrl] = None
    document_id: Optional[str] = None
    video_style: str = "tutorial"
    video_duration: int = 10
    custom_prompt: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_source(self):
        if not self.url and not self.document_id:
            raise ValueError("Either url or document_id must be provided")
        if self.url and self.document_id:
            raise ValueError("Cannot provide both url and document_id")
        return self

class ScriptPreviewResponse(BaseModel):
    script: str
    source: str  # URL or document title
    source_type: str  # "url", "github_repo", or "document"
    video_duration: int

class VideoCreateWithScriptRequest(BaseModel):
    url: Optional[HttpUrl] = None
    document_id: Optional[str] = None
    script: str
    avatar_type: str = "professional_female"
    voice_type: str = "tr_female_professional"
    video_style: str = "tutorial"
    provider: str = "heygen"
    video_duration: int = 10
    mode: str = "avatar"
    scroll_speed: str = "medium"
    custom_prompt: Optional[str] = None
    custom_avatar_image_id: Optional[str] = None  # For custom_avatar_overlay mode
    
    @model_validator(mode='after')
    def validate_source(self):
        # Script is already provided, so url/document_id is optional
        # Only validate if both are provided (cannot have both)
        if self.url and self.document_id:
            raise ValueError("Cannot provide both url and document_id")
        
        # Custom avatar images only work with D-ID provider
        if hasattr(self, 'custom_avatar_image_id') and self.custom_avatar_image_id and hasattr(self, 'provider') and self.provider != "did":
            raise ValueError("Custom avatar images require D-ID provider. Please select 'did' as provider.")
        
        return self

class GitHubAnalyzer:
    """GitHub repository analysis service"""
    
    @staticmethod
    async def analyze_repo(url: str) -> Dict:
        """Extract GitHub repository information"""
        try:
            # Clean up URL and remove .git suffix only from the end
            clean_url = url.replace("https://github.com/", "").replace("http://github.com/", "")
            clean_url = clean_url.rstrip("/")
            # Only remove .git if it's at the end of the URL
            if clean_url.endswith(".git"):
                clean_url = clean_url[:-4]
            parts = clean_url.split("/")
            if len(parts) < 2:
                raise ValueError("Invalid GitHub URL")
            
            owner, repo_name = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url)
                response.raise_for_status()
                repo_data = response.json()
                
                readme_content = "README not found"
                try:
                    readme_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
                    readme_response = await client.get(readme_url)
                    readme_json = readme_response.json()
                    readme_content = base64.b64decode(readme_json.get("content", "")).decode("utf-8")
                except Exception as e:
                    print(f"⚠️ Could not fetch README: {str(e)}")
                
                languages = {}
                try:
                    lang_url = f"https://api.github.com/repos/{owner}/{repo_name}/languages"
                    lang_response = await client.get(lang_url)
                    languages = lang_response.json()
                except Exception as e:
                    print(f"⚠️ Could not fetch languages: {str(e)}")
                
                return {
                    "name": repo_data.get("name"),
                    "full_name": repo_data.get("full_name"),
                    "description": repo_data.get("description", "No description"),
                    "language": repo_data.get("language", "Not specified"),
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "watchers": repo_data.get("watchers_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "topics": repo_data.get("topics", []),
                    "created_at": repo_data.get("created_at"),
                    "updated_at": repo_data.get("updated_at"),
                    "homepage": repo_data.get("homepage"),
                    "readme": readme_content[:3000],
                    "license": repo_data.get("license", {}).get("name", "Not specified") if repo_data.get("license") else "Not specified",
                    "languages": languages,
                    "owner": owner,
                    "repo": repo_name
                }
        
        except Exception as e:
            raise Exception(f"GitHub analysis error: {str(e)}")

class ScriptGenerator:
    """AI-powered script generation service"""
    
    @staticmethod
    async def generate_script(repo_data: Dict, style: str, video_duration: int = 10, custom_prompt: Optional[str] = None) -> Dict:
        """Generate Turkish video script using AI based on duration
        
        Args:
            repo_data: Content/repository data
            style: Video style (tutorial, review, quick_start)
            video_duration: Video duration in minutes (5, 10, or 15)
            custom_prompt: Optional custom instructions from user
        """
        
        from services.ai_service import AIService
        
        ai_service = AIService()
        script_text = await ai_service.generate_turkish_script(repo_data, style, video_duration, custom_prompt=custom_prompt)
        
        sections = []
        current_section = None
        
        for line in script_text.strip().split('\n'):
            # Check for section markers like **[00:00-00:20] or [00:00]
            if '**[' in line or (line.startswith('[') and ']' in line):
                if current_section:
                    sections.append(current_section)
                
                # Extract timestamp and title
                if '**[' in line:
                    # Format: **[00:00-00:20] TITLE**
                    parts = line.replace('**', '').strip()
                    if '[' in parts and ']' in parts:
                        timestamp_part = parts[parts.find('[') + 1:parts.find(']')]
                        title_part = parts[parts.find(']') + 1:].strip()
                    else:
                        timestamp_part = "00:00"
                        title_part = line
                else:
                    # Format: [00:00] TITLE
                    timestamp_part = line.split(']')[0].replace('[', '')
                    title_part = line.split(']')[1].strip() if ']' in line else ""
                
                # All sections are avatar-based for video generation
                section_type = "avatar"
                
                current_section = {
                    "timestamp": timestamp_part,
                    "title": title_part,
                    "type": section_type,
                    "text": ""
                }
                print(f"📝 Found section: {title_part[:50]}")
            elif current_section and line.strip() and not line.startswith('---'):
                # Add non-empty lines to current section (skip separators like ---)
                current_section["text"] += line + "\n"
        
        if current_section:
            sections.append(current_section)
        
        # If no sections were parsed, create a single default section with all text
        if not sections and script_text.strip():
            print("⚠️ No sections found in script, creating default section")
            sections = [{
                "timestamp": "00:00",
                "title": "Video Content",
                "type": "avatar",
                "text": script_text
            }]
        
        print(f"✅ Parsed {len(sections)} sections from script")
        
        # Format duration string
        duration_str = f"{video_duration:02d}:00"
        
        return {
            "full_text": script_text,
            "sections": sections,
            "metadata": {
                "word_count": len(script_text.split()),
                "estimated_duration": duration_str,
                "language": "tr"
            }
        }

class TTSService:
    """ElevenLabs Text-to-Speech service"""
    
    @staticmethod
    async def generate_audio(script, voice_type: str) -> str:
        """Generate Turkish audio using ElevenLabs
        
        Args:
            script: Can be either a dict with 'full_text' key or a string
            voice_type: Voice type for TTS
        """
        
        from services.elevenlabs_service import ElevenLabsService
        
        # Handle both dict and string inputs
        if isinstance(script, dict):
            script_text = script.get("full_text", "")
        else:
            script_text = str(script)
        
        elevenlabs = ElevenLabsService()
        audio_path = await elevenlabs.text_to_speech(script_text, voice_type)
        
        return audio_path

class AvatarService:
    """Avatar video rendering service (supports D-ID and HeyGen)"""
    
    @staticmethod
    async def render_avatar_segments(script: Dict, avatar_type: str, audio_file: str, provider: str = "heygen") -> List[str]:
        """Render avatar video segments using selected provider API"""
        
        # Select provider service
        if provider == "heygen":
            from services.heygen_service import HeyGenService
            service = HeyGenService()
            print(f"🎭 Using HeyGen service (enabled: {service.enabled})")
        else:
            from services.did_service import DIDService
            service = DIDService()
            print(f"🎭 Using D-ID service (enabled: {service.enabled})")
        
        avatar_videos = []
        
        for i, section in enumerate(script["sections"]):
            if section["type"] == "avatar":
                print(f"📹 Processing section {i+1}/{len(script['sections'])}: {section.get('title', 'No title')[:50]}")
                try:
                    video_path = await service.create_avatar_video(
                        text=section["text"],
                        avatar_type=avatar_type
                    )
                    avatar_videos.append(video_path)
                    print(f"✅ Section {i+1} video created: {video_path}")
                except Exception as e:
                    print(f"❌ Error creating avatar video for section {i+1}: {str(e)}")
                    continue
        
        print(f"📊 Total avatar videos created: {len(avatar_videos)}")
        return avatar_videos

async def update_progress(video_id: str, progress: int, stage: str):
    """Update video processing progress"""
    if video_id in videos_db:
        videos_db[video_id]["progress"] = progress
        videos_db[video_id]["current_stage"] = stage
        await save_videos_db(videos_db)  # Save changes to disk

async def process_video_pipeline_with_script(video_id: str, request: VideoCreateWithScriptRequest):
    """Video generation pipeline with pre-approved script"""
    try:
        videos_db[video_id]["created_at"] = datetime.now().isoformat()
        await save_videos_db(videos_db)
        
        # Use the approved script directly
        script = videos_db[video_id].get("approved_script", request.script)
        
        # Ensure script is a string (safeguard)
        if isinstance(script, dict):
            script = script.get("full_text", str(script))
        
        if request.mode == "custom_avatar_overlay":
            # Custom avatar overlay pipeline with approved script
            await update_progress(video_id, 10, "🎬 Recording screen with browser automation...")
            
            # Determine source URL
            if request.url:
                source_url = str(request.url)
            elif request.document_id:
                # Screen recording requires URL
                raise Exception("Doküman için screen recording modu desteklenmez. Lütfen avatar modu kullanın.")
            else:
                raise Exception("URL veya document_id gerekli")
            
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            screen_video = await recorder.record_website(
                url=source_url,
                video_id=video_id,
                duration_minutes=request.video_duration,
                scroll_speed=request.scroll_speed
            )
            
            await update_progress(video_id, 35, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            await update_progress(video_id, 60, "🎭 Creating custom avatar video with lip-sync...")
            # Get custom image path - check both jpg and png
            custom_image_path = None
            if request.custom_avatar_image_id:
                # Check which format was uploaded
                jpg_path = f"videos/uploads/{request.custom_avatar_image_id}.jpg"
                png_path = f"videos/uploads/{request.custom_avatar_image_id}.png"
                
                from pathlib import Path
                if Path(jpg_path).exists():
                    custom_image_path = jpg_path
                elif Path(png_path).exists():
                    custom_image_path = png_path
                else:
                    print(f"⚠️ Custom image not found: {request.custom_avatar_image_id}")
                    custom_image_path = None
            
            # Create avatar video with custom photo
            from services.did_service import DIDService
            did_service = DIDService()
            avatar_video = await did_service.create_avatar_video(
                text=str(script),
                avatar_type=request.avatar_type,
                custom_image_path=custom_image_path,
                audio_path=audio_file  # Full 200s audio, bypasses text limit
            )
            
            await update_progress(video_id, 85, "🎬 Overlaying circular avatar on screen recording...")
            from services.video_composer import VideoComposer
            final_video = await VideoComposer.overlay_avatar_on_screen_recording(
                screen_video=screen_video,
                avatar_video=avatar_video,
                audio_file=audio_file,
                video_id=video_id,
                position="bottom_right"
            )
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)
            
        elif request.mode == "screen_recording":
            await update_progress(video_id, 10, "📊 Preparing screen recording...")
            
            # Determine source URL
            if request.url:
                source_url = str(request.url)
            elif request.document_id:
                # Screen recording requires URL
                raise Exception("Doküman için screen recording modu desteklenmez. Lütfen avatar modu kullanın.")
            else:
                raise Exception("URL veya document_id gerekli")
            
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            screen_video = await recorder.record_website(
                url=source_url,
                video_id=video_id,
                duration_minutes=request.video_duration,
                scroll_speed=request.scroll_speed
            )
            
            await update_progress(video_id, 50, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            await update_progress(video_id, 80, "🎬 Muxing screen recording with audio...")
            from services.video_composer import VideoComposer
            final_video = await VideoComposer.mux_screen_recording_with_audio(screen_video, audio_file, video_id)
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)
        else:
            await update_progress(video_id, 25, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            # Check for custom avatar image
            custom_image_path = None
            if hasattr(request, 'custom_avatar_image_id') and request.custom_avatar_image_id:
                # Check which format was uploaded
                jpg_path = f"videos/uploads/{request.custom_avatar_image_id}.jpg"
                png_path = f"videos/uploads/{request.custom_avatar_image_id}.png"
                
                from pathlib import Path
                if Path(jpg_path).exists():
                    custom_image_path = jpg_path
                    print(f"✅ Using custom avatar image: {jpg_path}")
                elif Path(png_path).exists():
                    custom_image_path = png_path
                    print(f"✅ Using custom avatar image: {png_path}")
                else:
                    print(f"⚠️ Custom image not found: {request.custom_avatar_image_id}")
            
            await update_progress(video_id, 50, f"🎭 Rendering avatar video segments with {request.provider.upper()}...")
            
            # If custom image provided, use D-ID directly (supports custom images)
            if custom_image_path:
                print("🖼️ Creating avatar video with custom photo...")
                from services.did_service import DIDService
                did_service = DIDService()
                avatar_video = await did_service.create_avatar_video(
                    text=str(script),
                    avatar_type=request.avatar_type,
                    custom_image_path=custom_image_path,
                    audio_path=audio_file  # Full 200s audio, bypasses text limit
                )
                
                await update_progress(video_id, 75, "🎬 Looping avatar video to match full audio...")
                from services.video_composer import VideoComposer
                # Use loop composer for custom photo (short D-ID clip)
                final_video = await VideoComposer.compose_video_with_loop(avatar_video, audio_file, video_id)
            else:
                # Standard avatar rendering - create single video from script text
                if request.provider == "heygen":
                    from services.heygen_service import HeyGenService
                    service = HeyGenService()
                else:
                    from services.did_service import DIDService
                    service = DIDService()
                
                avatar_video = await service.create_avatar_video(
                    text=str(script),
                    avatar_type=request.avatar_type
                )
                
                await update_progress(video_id, 75, "🎬 Composing final video...")
                from services.video_composer import VideoComposer
                # Mux avatar video with audio
                final_video = await VideoComposer.mux_screen_recording_with_audio(avatar_video, audio_file, video_id)
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)
            
    except Exception as e:
        error_msg = "Video işleme sırasında bir hata oluştu"
        if "timeout" in str(e).lower():
            error_msg = "Video oluşturma zaman aşımına uğradı"
        elif "api" in str(e).lower():
            error_msg = "API servisi ile bağlantı kurulamadı"
        
        videos_db[video_id]["status"] = "failed"
        videos_db[video_id]["error"] = error_msg
        videos_db[video_id]["current_stage"] = f"❌ Hata: {error_msg}"
        print(f"❌ Pipeline error for {video_id}: {str(e)}")
        await save_videos_db(videos_db)

async def process_video_pipeline(video_id: str, request: VideoCreateRequest):
    """Main video generation pipeline"""
    try:
        videos_db[video_id]["created_at"] = datetime.now().isoformat()
        await save_videos_db(videos_db)  # Save changes to disk
        
        # Check mode: screen_recording, avatar, or custom_avatar_overlay
        if request.mode == "custom_avatar_overlay":
            # Custom avatar overlay pipeline: Screen recording + custom photo avatar overlay
            await update_progress(video_id, 5, "📊 Analyzing content...")
            await asyncio.sleep(1)
            
            from services.website_analyzer import ContentAnalyzer
            
            # Get content based on source type
            if request.url:
                repo_data = await ContentAnalyzer.analyze_url(str(request.url))
                source_url = str(request.url)
            elif request.document_id:
                from pathlib import Path as PathLib
                doc_path = PathLib("videos/uploads/documents")
                doc_files = list(doc_path.glob(f"{request.document_id}.*"))
                if not doc_files:
                    raise Exception("Doküman bulunamadı")
                doc_file = doc_files[0]
                repo_data = await ContentAnalyzer.analyze_document(str(doc_file), doc_file.name)
                source_url = None  # No URL for documents
            else:
                raise Exception("URL veya document_id gerekli")
            
            await update_progress(video_id, 15, f"🎬 Recording screen with browser automation...")
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            
            # Screen recording requires URL
            if not source_url:
                raise Exception("Doküman için screen recording modu desteklenmez. Lütfen avatar modu kullanın.")
            
            screen_video = await recorder.record_website(
                url=source_url,
                video_id=video_id,
                duration_minutes=request.video_duration,
                scroll_speed=request.scroll_speed
            )
            
            await update_progress(video_id, 35, f"✍️ Generating {request.video_duration}-minute Turkish narration script with AI...")
            script = await ScriptGenerator.generate_script(repo_data, request.video_style, request.video_duration, custom_prompt=getattr(request, 'custom_prompt', None))
            
            await update_progress(video_id, 50, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            await update_progress(video_id, 65, "🎭 Creating custom avatar video with lip-sync...")
            # Get custom image path - check both jpg and png
            custom_image_path = None
            if request.custom_avatar_image_id:
                from pathlib import Path
                jpg_path = f"videos/uploads/{request.custom_avatar_image_id}.jpg"
                png_path = f"videos/uploads/{request.custom_avatar_image_id}.png"
                
                if Path(jpg_path).exists():
                    custom_image_path = jpg_path
                elif Path(png_path).exists():
                    custom_image_path = png_path
                else:
                    print(f"⚠️ Custom image not found: {request.custom_avatar_image_id}")
            
            # Create avatar video with custom photo
            from services.did_service import DIDService
            did_service = DIDService()
            avatar_video = await did_service.create_avatar_video(
                text=str(script),
                avatar_type=request.avatar_type,
                custom_image_path=custom_image_path,
                audio_path=audio_file  # Full 200s audio, bypasses text limit
            )
            
            await update_progress(video_id, 85, "🎬 Overlaying circular avatar on screen recording...")
            from services.video_composer import VideoComposer
            final_video = await VideoComposer.overlay_avatar_on_screen_recording(
                screen_video=screen_video,
                avatar_video=avatar_video,
                audio_file=audio_file,
                video_id=video_id,
                position="bottom_right"
            )
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)  # Save changes to disk
            
        elif request.mode == "screen_recording":
            # Screen recording pipeline (FAST!)
            await update_progress(video_id, 10, "📊 Analyzing content...")
            await asyncio.sleep(1)
            
            from services.website_analyzer import ContentAnalyzer
            
            # Get content based on source type
            if request.url:
                repo_data = await ContentAnalyzer.analyze_url(str(request.url))
                source_url = str(request.url)
            elif request.document_id:
                # Screen recording mode does not support documents
                raise Exception("Doküman için screen recording modu desteklenmez. Lütfen avatar modu kullanın.")
            else:
                raise Exception("URL veya document_id gerekli")
            
            await update_progress(video_id, 20, f"🎬 Recording screen with browser automation...")
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            screen_video = await recorder.record_website(
                url=source_url,
                video_id=video_id,
                duration_minutes=request.video_duration,
                scroll_speed=request.scroll_speed
            )
            
            await update_progress(video_id, 50, f"✍️ Generating {request.video_duration}-minute Turkish narration script with AI...")
            script = await ScriptGenerator.generate_script(repo_data, request.video_style, request.video_duration, custom_prompt=getattr(request, 'custom_prompt', None))
            
            await update_progress(video_id, 70, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            await update_progress(video_id, 90, "🎬 Muxing screen recording with audio...")
            from services.video_composer import VideoComposer
            final_video = await VideoComposer.mux_screen_recording_with_audio(screen_video, audio_file, video_id)
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)  # Save changes to disk
            
        else:
            # Original avatar pipeline
            await update_progress(video_id, 10, "📊 Analyzing content...")
            await asyncio.sleep(1)
            
            from services.website_analyzer import ContentAnalyzer
            
            # Get content based on source type
            if request.url:
                repo_data = await ContentAnalyzer.analyze_url(str(request.url))
            elif request.document_id:
                from pathlib import Path as PathLib
                doc_path = PathLib("videos/uploads/documents")
                doc_files = list(doc_path.glob(f"{request.document_id}.*"))
                if not doc_files:
                    raise Exception("Doküman bulunamadı")
                doc_file = doc_files[0]
                repo_data = await ContentAnalyzer.analyze_document(str(doc_file), doc_file.name)
            else:
                raise Exception("URL veya document_id gerekli")
            
            await update_progress(video_id, 25, f"✍️ Generating {request.video_duration}-minute Turkish script with AI...")
            script = await ScriptGenerator.generate_script(repo_data, request.video_style, request.video_duration, custom_prompt=getattr(request, 'custom_prompt', None))
            
            await update_progress(video_id, 45, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            # Check for custom avatar image
            custom_image_path = None
            if hasattr(request, 'custom_avatar_image_id') and request.custom_avatar_image_id:
                # Check which format was uploaded
                jpg_path = f"videos/uploads/{request.custom_avatar_image_id}.jpg"
                png_path = f"videos/uploads/{request.custom_avatar_image_id}.png"
                
                from pathlib import Path
                if Path(jpg_path).exists():
                    custom_image_path = jpg_path
                    print(f"✅ Using custom avatar image: {jpg_path}")
                elif Path(png_path).exists():
                    custom_image_path = png_path
                    print(f"✅ Using custom avatar image: {png_path}")
                else:
                    print(f"⚠️ Custom image not found: {request.custom_avatar_image_id}")
            
            await update_progress(video_id, 65, f"🎭 Rendering avatar video segments with {request.provider.upper()}...")
            
            # If custom image provided, use D-ID directly (supports custom images)
            if custom_image_path:
                print("🖼️ Creating avatar video with custom photo...")
                from services.did_service import DIDService
                did_service = DIDService()
                avatar_video = await did_service.create_avatar_video(
                    text=str(script),
                    avatar_type=request.avatar_type,
                    custom_image_path=custom_image_path,
                    audio_path=audio_file  # Full 200s audio, bypasses text limit
                )
                
                await update_progress(video_id, 85, "🎬 Looping avatar video to match full audio...")
                from services.video_composer import VideoComposer
                # Use loop composer for custom photo (short D-ID clip)
                final_video = await VideoComposer.compose_video_with_loop(avatar_video, audio_file, video_id)
            else:
                # Standard avatar rendering
                avatar_videos = await AvatarService.render_avatar_segments(script, request.avatar_type, audio_file, request.provider)
                
                await update_progress(video_id, 85, "🎬 Composing final video...")
                from services.video_composer import VideoComposer
                composer = VideoComposer()
                final_video = await composer.compose_video(avatar_videos, audio_file, video_id)
            
            await update_progress(video_id, 100, "✅ Video completed successfully!")
            videos_db[video_id]["status"] = "completed"
            videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
            videos_db[video_id]["video_path"] = final_video
            videos_db[video_id]["completed_at"] = datetime.now().isoformat()
            await save_videos_db(videos_db)  # Save changes to disk
        
    except Exception as e:
        # Sanitize error message to prevent information disclosure
        error_msg = "Video işleme sırasında bir hata oluştu"
        if "timeout" in str(e).lower():
            error_msg = "Video oluşturma zaman aşımına uğradı"
        elif "api" in str(e).lower():
            error_msg = "API servisi ile bağlantı kurulamadı"
        
        videos_db[video_id]["status"] = "failed"
        videos_db[video_id]["error"] = error_msg
        videos_db[video_id]["current_stage"] = f"❌ Hata: {error_msg}"
        print(f"❌ Pipeline error for {video_id}: {str(e)}")  # Log actual error
        await save_videos_db(videos_db)  # Save changes to disk

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main web interface"""
    html_content = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Avatar Video Maker</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-purple-100 to-blue-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-4xl font-bold text-center mb-2 text-purple-900">🎬 AI Avatar Video Maker</h1>
            <p class="text-center text-gray-600 mb-4">Herhangi bir web sitesi veya GitHub projesinden otomatik Türkçe eğitim videoları oluşturun</p>
            
            <!-- API Status Indicator -->
            <div id="apiStatus" class="mb-6 bg-white rounded-lg shadow-md p-4">
                <h3 class="text-sm font-medium text-gray-700 mb-2">🔌 API Durumu</h3>
                <div id="statusIndicators" class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    <div class="flex items-center"><span class="w-2 h-2 bg-gray-300 rounded-full mr-2"></span> AI: Kontrol ediliyor...</div>
                    <div class="flex items-center"><span class="w-2 h-2 bg-gray-300 rounded-full mr-2"></span> Ses: Kontrol ediliyor...</div>
                    <div class="flex items-center"><span class="w-2 h-2 bg-gray-300 rounded-full mr-2"></span> Avatar: Kontrol ediliyor...</div>
                    <div class="flex items-center"><span class="w-2 h-2 bg-gray-300 rounded-full mr-2"></span> Genel: Kontrol ediliyor...</div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-xl p-6 mb-6">
                <h2 class="text-2xl font-semibold mb-4">Yeni Video Oluştur</h2>
                
                <div class="space-y-4">
                    <!-- Tab System for URL vs Document -->
                    <div class="mb-4">
                        <div class="flex gap-2 mb-4 border-b border-gray-200">
                            <button id="urlTabBtn" onclick="switchTab('url')" class="px-4 py-2 font-medium text-purple-600 border-b-2 border-purple-600 transition-colors">
                                🌐 Web Sitesi / URL
                            </button>
                            <button id="documentTabBtn" onclick="switchTab('document')" class="px-4 py-2 font-medium text-gray-500 hover:text-purple-600 transition-colors">
                                📄 Doküman Yükle
                            </button>
                        </div>
                        
                        <!-- URL Tab -->
                        <div id="urlTab">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Web Sitesi veya GitHub URL</label>
                            <input type="text" id="githubUrl" placeholder="https://example.com veya https://github.com/owner/repo" 
                                   class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent">
                            <p class="text-xs text-gray-500 mt-1">✨ Herhangi bir web sitesi URL'i girin - otomatik analiz edilecek!</p>
                        </div>
                        
                        <!-- Document Tab -->
                        <div id="documentTab" class="hidden">
                            <label class="block text-sm font-medium text-gray-700 mb-2">📄 Doküman Yükle (PDF, DOCX, TXT, MD)</label>
                            <input type="file" id="documentFile" accept="application/pdf,.pdf,.docx,.txt,.md,.markdown" 
                                   onchange="handleDocumentUpload()"
                                   class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white">
                            <p class="text-xs text-gray-500 mt-2">📁 Maksimum dosya boyutu: 10MB | Desteklenen formatlar: PDF, DOCX, TXT, MD</p>
                            
                            <!-- Document Upload Status -->
                            <div id="documentUploadStatus" class="mt-3 hidden"></div>
                            
                            <!-- Document Preview -->
                            <div id="documentPreview" class="mt-4 hidden bg-gray-50 border border-gray-200 rounded-lg p-4">
                                <h4 class="text-sm font-semibold text-gray-700 mb-2">📋 Yüklenen Doküman:</h4>
                                <div class="space-y-1 text-sm">
                                    <p><strong>Dosya:</strong> <span id="docFileName"></span></p>
                                    <p><strong>Kelime Sayısı:</strong> <span id="docWordCount"></span></p>
                                    <p class="text-xs text-gray-600 mt-2"><strong>Önizleme:</strong></p>
                                    <p id="docPreviewText" class="text-xs text-gray-600 bg-white p-2 rounded border border-gray-200 max-h-20 overflow-y-auto"></p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Custom Prompt/Instructions -->
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">💬 Özel Talimatlar (İsteğe Bağlı)</label>
                        <textarea id="customPrompt" rows="3" 
                                  placeholder="Örnek: 'Videoda başlangıç seviyesindeki kullanıcılara odaklan', 'Kod örneklerini detaylı açıkla', 'Kurulum adımlarını tek tek göster'..." 
                                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"></textarea>
                        <p class="text-xs text-gray-500 mt-1">💡 AI'a özel isteklerinizi yazın - script buna göre hazırlanacak!</p>
                    </div>
                    
                    <!-- Video Mode Selection -->
                    <div class="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">🎥 Video Oluşturma Modu</label>
                        <select id="videoMode" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" onchange="toggleModeOptions()">
                            <option value="screen_recording">🚀 Sadece Ekran Kaydı + Ses (Hızlı - Avatar YOK)</option>
                            <option value="custom_avatar_overlay">📸 Ekran Kaydı + Fotoğraflı Avatar Overlay (Köşede siz konuşursunuz!)</option>
                            <option value="avatar">👤 Sadece AI Avatar (Yavaş - Web sitesi YOK)</option>
                        </select>
                        <p class="text-xs text-blue-600 mt-2">
                            💡 <strong>Fotoğrafınızla video yapmak için:</strong> "Ekran Kaydı + Fotoğraflı Avatar" seçin → Fotoğraf yükleyin → Script onaylayın
                        </p>
                    </div>
                    
                    <!-- Custom Avatar Photo Upload (for custom_avatar_overlay mode) -->
                    <div id="customAvatarUpload" class="hidden mb-4 bg-purple-50 border border-purple-200 rounded-lg p-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">📷 Fotoğrafınızı Yükleyin</label>
                        <input type="file" id="avatarPhoto" accept="image/jpeg,image/png,image/jpg" 
                               onchange="handlePhotoUpload()"
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white">
                        <p class="text-xs text-purple-600 mt-2">✨ Fotoğrafınız konuşacak ve videonun köşesinde yuvarlak çerçevede görünecek! (Max 5MB, JPG/PNG)</p>
                        <p class="text-xs text-amber-600 mt-1 font-medium">⚠️ Önemli: Kendi fotoğrafınız için Provider'da "D-ID" seçili olmalı (HeyGen desteklemiyor)</p>
                        <div id="photoPreview" class="mt-3 hidden">
                            <p class="text-sm text-gray-600 mb-2">Önizleme:</p>
                            <img id="photoPreviewImg" class="w-24 h-24 rounded-full object-cover border-4 border-purple-400" />
                        </div>
                        <div id="uploadStatus" class="mt-2 hidden text-sm"></div>
                    </div>
                    
                    <!-- Scroll Speed (for screen recording) -->
                    <div id="scrollSpeedOption" class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">🖱️ Scroll Hızı</label>
                        <select id="scrollSpeed" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                            <option value="slow">Yavaş (Detaylı gösterim)</option>
                            <option value="medium" selected>Orta (Dengeli)</option>
                            <option value="fast">Hızlı (Özet)</option>
                        </select>
                    </div>
                    
                    <div id="avatarOptions" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 hidden">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Video Süresi</label>
                            <select id="videoDuration" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="5">5 Dakika (Hızlı)</option>
                                <option value="10" selected>10 Dakika (Normal)</option>
                                <option value="15">15 Dakika (Detaylı)</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Avatar Sağlayıcı</label>
                            <select id="provider" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="heygen">HeyGen (Önerilen)</option>
                                <option value="did">D-ID</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Avatar Tipi</label>
                            <select id="avatarType" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="professional_female">Profesyonel Kadın</option>
                                <option value="professional_male">Profesyonel Erkek</option>
                                <option value="casual_female">Rahat Kadın</option>
                                <option value="casual_male">Rahat Erkek</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Ses Tipi</label>
                            <select id="voiceType" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="tr_female_professional">Türkçe Profesyonel Kadın</option>
                                <option value="tr_male_professional">Türkçe Profesyonel Erkek</option>
                                <option value="tr_female_friendly">Türkçe Samimi Kadın</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Video Stili</label>
                            <select id="videoStyle" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="tutorial">Eğitim</option>
                                <option value="review">İnceleme</option>
                                <option value="quick_start">Hızlı Başlangıç</option>
                            </select>
                        </div>
                    </div>
                    
                    <!-- Common Options (always visible) -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Video Süresi</label>
                            <select id="commonDuration" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="5">5 Dakika (Hızlı)</option>
                                <option value="10" selected>10 Dakika (Normal)</option>
                                <option value="15">15 Dakika (Detaylı)</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Ses Tipi</label>
                            <select id="commonVoiceType" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="tr_female_professional">Türkçe Profesyonel Kadın</option>
                                <option value="tr_male_professional">Türkçe Profesyonel Erkek</option>
                                <option value="tr_female_friendly">Türkçe Samimi Kadın</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Video Stili</label>
                            <select id="commonVideoStyle" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500">
                                <option value="tutorial">Eğitim</option>
                                <option value="review">İnceleme</option>
                                <option value="quick_start">Hızlı Başlangıç</option>
                            </select>
                        </div>
                    </div>
                    
                    <button onclick="previewScript()" 
                            class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition duration-200">
                        📝 Script Önizle
                    </button>
                </div>
            </div>
            
            <!-- Script Preview Panel -->
            <div id="scriptPreview" class="hidden bg-white rounded-lg shadow-xl p-6 mb-6">
                <h2 class="text-2xl font-semibold mb-4">📝 Script Önizlemesi</h2>
                
                <div id="scriptLoading" class="text-center py-8">
                    <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    <p class="mt-4 text-gray-600">Script oluşturuluyor...</p>
                </div>
                
                <div id="scriptContent" class="hidden">
                    <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p class="text-sm text-blue-800">✍️ Scripti istediğiniz gibi düzenleyebilir veya direkt olarak onaylayabilirsiniz</p>
                    </div>
                    
                    <textarea id="scriptText" rows="20" 
                              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm mb-4"></textarea>
                    
                    <div class="flex gap-3">
                        <button onclick="approveScript()" 
                                class="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition">
                            ✅ Onayla ve Video Oluştur
                        </button>
                        <button onclick="cancelScript()" 
                                class="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 transition">
                            ❌ İptal Et
                        </button>
                    </div>
                </div>
            </div>
            
            <div id="videoStatus" class="hidden bg-white rounded-lg shadow-xl p-6">
                <h2 class="text-2xl font-semibold mb-4">Video İşleme Durumu</h2>
                
                <div class="mb-4">
                    <div class="flex justify-between mb-2">
                        <span class="text-sm font-medium text-gray-700" id="statusText">Başlatılıyor...</span>
                        <span class="text-sm font-medium text-gray-700" id="progressPercent">0%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-4">
                        <div id="progressBar" class="bg-purple-600 h-4 rounded-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                </div>
                
                <div id="videoResult" class="hidden mt-4">
                    <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                        <p class="text-green-800 font-semibold mb-3">✅ Video başarıyla oluşturuldu!</p>
                        
                        <!-- Video Player -->
                        <div class="bg-black rounded-lg overflow-hidden mb-4">
                            <video id="videoPlayer" controls class="w-full" controlsList="nodownload">
                                <source id="videoSource" src="" type="video/mp4">
                                Tarayıcınız video etiketini desteklemiyor.
                            </video>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="flex gap-3 mb-4">
                            <button onclick="downloadVideo()" id="downloadBtn" class="flex-1 bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition">
                                📥 Videoyu İndir
                            </button>
                            <button onclick="toggleEditOptions()" class="flex-1 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition">
                                ✏️ Düzenle
                            </button>
                        </div>
                    </div>
                    
                    <!-- Edit Options -->
                    <div id="editOptions" class="hidden bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h3 class="text-lg font-semibold text-blue-900 mb-3">🎨 Video Düzenleme Seçenekleri</h3>
                        <p class="text-sm text-blue-700 mb-4">Farklı avatar, ses veya stil ile videoyu yeniden oluşturun</p>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Yeni Video Süresi</label>
                                <select id="editVideoDuration" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                    <option value="5">5 Dakika (Hızlı)</option>
                                    <option value="10">10 Dakika (Normal)</option>
                                    <option value="15">15 Dakika (Detaylı)</option>
                                </select>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Yeni Avatar Sağlayıcı</label>
                                <select id="editProvider" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                    <option value="heygen">HeyGen (Önerilen)</option>
                                    <option value="did">D-ID</option>
                                </select>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Yeni Avatar Tipi</label>
                                <select id="editAvatarType" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                    <option value="professional_female">Profesyonel Kadın</option>
                                    <option value="professional_male">Profesyonel Erkek</option>
                                    <option value="casual_female">Rahat Kadın</option>
                                    <option value="casual_male">Rahat Erkek</option>
                                </select>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Yeni Ses Tipi</label>
                                <select id="editVoiceType" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                    <option value="tr_female_professional">Türkçe Profesyonel Kadın</option>
                                    <option value="tr_male_professional">Türkçe Profesyonel Erkek</option>
                                    <option value="tr_female_friendly">Türkçe Samimi Kadın</option>
                                </select>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Yeni Video Stili</label>
                                <select id="editVideoStyle" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                    <option value="tutorial">Eğitim</option>
                                    <option value="review">İnceleme</option>
                                    <option value="quick_start">Hızlı Başlangıç</option>
                                </select>
                            </div>
                        </div>
                        
                        <button onclick="recreateVideo()" class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition">
                            🔄 Yeniden Oluştur
                        </button>
                    </div>
                </div>
                
                <div id="errorResult" class="hidden mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-red-800 font-semibold" id="errorText">❌ Hata oluştu</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        console.log('✅ Script loaded successfully!');
        let currentVideoId = null;
        let currentVideoUrl = null;
        let statusInterval = null;
        let activeTab = 'url'; // Track active tab: 'url' or 'document'
        let uploadedDocumentId = null; // Store uploaded document ID
        
        // Tab switching function
        function switchTab(tab) {
            activeTab = tab;
            
            const urlTab = document.getElementById('urlTab');
            const documentTab = document.getElementById('documentTab');
            const urlTabBtn = document.getElementById('urlTabBtn');
            const documentTabBtn = document.getElementById('documentTabBtn');
            const videoMode = document.getElementById('videoMode');
            
            if (tab === 'url') {
                // Show URL tab
                urlTab.classList.remove('hidden');
                documentTab.classList.add('hidden');
                urlTabBtn.classList.add('text-purple-600', 'border-b-2', 'border-purple-600');
                urlTabBtn.classList.remove('text-gray-500');
                documentTabBtn.classList.remove('text-purple-600', 'border-b-2', 'border-purple-600');
                documentTabBtn.classList.add('text-gray-500');
                
                // Re-enable all video modes for URL
                videoMode.innerHTML = `
                    <option value="screen_recording">🚀 Sadece Ekran Kaydı + Ses (Hızlı - Avatar YOK)</option>
                    <option value="custom_avatar_overlay">📸 Ekran Kaydı + Fotoğraflı Avatar Overlay (Köşede siz konuşursunuz!)</option>
                    <option value="avatar">👤 Sadece AI Avatar (Yavaş - Web sitesi YOK)</option>
                `;
            } else {
                // Show Document tab
                urlTab.classList.add('hidden');
                documentTab.classList.remove('hidden');
                documentTabBtn.classList.add('text-purple-600', 'border-b-2', 'border-purple-600');
                documentTabBtn.classList.remove('text-gray-500');
                urlTabBtn.classList.remove('text-purple-600', 'border-b-2', 'border-purple-600');
                urlTabBtn.classList.add('text-gray-500');
                
                // Disable screen recording mode for documents
                videoMode.innerHTML = `
                    <option value="avatar">👤 AI Avatar (Önerilen)</option>
                    <option value="custom_avatar_overlay" disabled>📸 Ekran Kaydı + Avatar (⚠️ Sadece URL için)</option>
                    <option value="screen_recording" disabled>🚀 Ekran Kaydı (⚠️ Sadece URL için)</option>
                `;
                videoMode.value = 'avatar';
            }
            
            toggleModeOptions();
        }
        
        // Document upload handler
        async function handleDocumentUpload() {
            const documentFile = document.getElementById('documentFile');
            const file = documentFile.files[0];
            const uploadStatus = document.getElementById('documentUploadStatus');
            const documentPreview = document.getElementById('documentPreview');
            
            if (!file) {
                uploadedDocumentId = null;
                documentPreview.classList.add('hidden');
                uploadStatus.classList.add('hidden');
                return;
            }
            
            // Check file size (10MB max)
            if (file.size > 10 * 1024 * 1024) {
                uploadStatus.classList.remove('hidden');
                uploadStatus.className = 'mt-3 text-sm text-red-600';
                uploadStatus.textContent = '❌ Dosya boyutu 10MB' + String.fromCharCode(39) + 'dan küçük olmalıdır!';
                documentFile.value = '';
                uploadedDocumentId = null;
                return;
            }
            
            // Show upload progress
            uploadStatus.classList.remove('hidden');
            uploadStatus.className = 'mt-3 text-sm text-blue-600';
            uploadStatus.textContent = '⏳ Doküman yükleniyor ve analiz ediliyor...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/uploads/document', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    let errorMsg = 'Doküman yüklenemedi';
                    try {
                        const error = await response.json();
                        errorMsg = error.detail || errorMsg;
                    } catch (e) {
                        errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMsg);
                }
                
                const result = await response.json();
                uploadedDocumentId = result.document_id;
                
                // Show success and preview
                uploadStatus.className = 'mt-3 text-sm text-green-600';
                uploadStatus.textContent = '✅ Doküman başarıyla yüklendi ve analiz edildi!';
                
                // Display document info
                document.getElementById('docFileName').textContent = result.filename;
                document.getElementById('docWordCount').textContent = result.word_count;
                document.getElementById('docPreviewText').textContent = result.preview;
                documentPreview.classList.remove('hidden');
                
            } catch (error) {
                console.error('Document upload error:', error);
                uploadStatus.className = 'mt-3 text-sm text-red-600';
                uploadStatus.textContent = '❌ Hata: ' + (error.message || 'Bilinmeyen hata');
                uploadedDocumentId = null;
                documentPreview.classList.add('hidden');
            }
        }
        
        // Check API status on page load
        function toggleModeOptions() {
            const mode = document.getElementById('videoMode').value;
            const avatarOptions = document.getElementById('avatarOptions');
            const scrollSpeedOption = document.getElementById('scrollSpeedOption');
            const customAvatarUpload = document.getElementById('customAvatarUpload');
            
            if (mode === 'avatar') {
                avatarOptions.classList.remove('hidden');
                scrollSpeedOption.classList.add('hidden');
                customAvatarUpload.classList.remove('hidden');
            } else if (mode === 'custom_avatar_overlay') {
                avatarOptions.classList.add('hidden');
                scrollSpeedOption.classList.remove('hidden');
                customAvatarUpload.classList.remove('hidden');
            } else {
                avatarOptions.classList.add('hidden');
                scrollSpeedOption.classList.remove('hidden');
                customAvatarUpload.classList.add('hidden');
            }
        }
        
        // Photo preview function
        document.addEventListener('DOMContentLoaded', function() {
            const photoInput = document.getElementById('avatarPhoto');
            if (photoInput) {
                photoInput.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (file) {
                        if (file.size > 5 * 1024 * 1024) {
                            alert('Dosya boyutu 5MB' + String.fromCharCode(39) + 'dan küçük olmalıdır!');
                            photoInput.value = '';
                            return;
                        }
                        
                        const reader = new FileReader();
                        reader.onload = function(event) {
                            const preview = document.getElementById('photoPreview');
                            const img = document.getElementById('photoPreviewImg');
                            img.src = event.target.result;
                            preview.classList.remove('hidden');
                        };
                        reader.readAsDataURL(file);
                    }
                });
            }
        });
        
        async function checkApiStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                const indicators = document.getElementById('statusIndicators');
                indicators.innerHTML = `
                    <div class="flex items-center">
                        <span class="w-2 h-2 ${status.overall.ai_available ? 'bg-green-400' : 'bg-red-400'} rounded-full mr-2"></span> 
                        AI: ${status.overall.ai_available ? 'Aktif' : 'İnaktif'}
                    </div>
                    <div class="flex items-center">
                        <span class="w-2 h-2 ${status.elevenlabs.enabled ? 'bg-green-400' : 'bg-red-400'} rounded-full mr-2"></span> 
                        Ses: ${status.elevenlabs.enabled ? 'Aktif' : 'İnaktif'} ${status.elevenlabs.note ? '⚠️' : ''}
                    </div>
                    <div class="flex items-center">
                        <span class="w-2 h-2 ${status.overall.avatar_available ? 'bg-green-400' : 'bg-red-400'} rounded-full mr-2"></span> 
                        Avatar: ${status.overall.avatar_available ? 'Aktif' : 'İnaktif'}
                    </div>
                    <div class="flex items-center">
                        <span class="w-2 h-2 ${status.overall.ready ? 'bg-green-400' : 'bg-red-400'} rounded-full mr-2"></span> 
                        Genel: ${status.overall.ready ? 'Hazır' : 'Hazır Değil'}
                    </div>
                `;
                
                // Update provider options based on availability
                const providerSelect = document.getElementById('provider');
                const editProviderSelect = document.getElementById('editProvider');
                
                if (status.heygen.enabled && !status.did.enabled) {
                    providerSelect.value = 'heygen';
                    editProviderSelect.value = 'heygen';
                } else if (!status.heygen.enabled && status.did.enabled) {
                    providerSelect.value = 'did';
                    editProviderSelect.value = 'did';
                }
            } catch (error) {
                console.error('API status check failed:', error);
            }
        }
        
        // Call on page load
        window.addEventListener('DOMContentLoaded', checkApiStatus);
        
        let currentScript = null;
        let uploadedPhotoId = null; // Store uploaded photo ID
        
        async function handlePhotoUpload() {
            const photoInput = document.getElementById('avatarPhoto');
            const file = photoInput.files[0];
            const uploadStatus = document.getElementById('uploadStatus');
            const photoPreview = document.getElementById('photoPreview');
            const photoPreviewImg = document.getElementById('photoPreviewImg');
            
            if (!file) {
                uploadedPhotoId = null;
                photoPreview.classList.add('hidden');
                uploadStatus.classList.add('hidden');
                return;
            }
            
            // Show preview immediately
            const reader = new FileReader();
            reader.onload = function(e) {
                photoPreviewImg.src = e.target.result;
                photoPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
            
            // Upload photo to server
            uploadStatus.classList.remove('hidden');
            uploadStatus.className = 'mt-2 text-sm text-blue-600';
            uploadStatus.textContent = '⏳ Fotoğraf yükleniyor...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/uploads/image', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    let errorMsg = 'Fotoğraf yüklenemedi';
                    try {
                        const error = await response.json();
                        errorMsg = error.detail || errorMsg;
                    } catch (e) {
                        errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMsg);
                }
                
                const result = await response.json();
                uploadedPhotoId = result.image_id;
                
                // Automatically switch to D-ID provider (required for custom avatars)
                const providerSelect = document.getElementById('provider');
                if (providerSelect && providerSelect.value !== 'did') {
                    providerSelect.value = 'did';
                    uploadStatus.className = 'mt-2 text-sm text-green-600';
                    uploadStatus.textContent = '✅ Fotoğraf yüklendi! Provider otomatik D-ID seçildi.';
                } else {
                    uploadStatus.className = 'mt-2 text-sm text-green-600';
                    uploadStatus.textContent = '✅ Fotoğraf başarıyla yüklendi!';
                }
            } catch (error) {
                console.error('Photo upload error:', error);
                uploadStatus.className = 'mt-2 text-sm text-red-600';
                uploadStatus.textContent = '❌ Hata: ' + (error.message || 'Bilinmeyen hata');
                uploadedPhotoId = null;
            }
        }
        
        console.log('🔧 About to define window.previewScript...');
        
        // Define globally accessible functions
        window.previewScript = async function() {
            const customPrompt = document.getElementById('customPrompt').value.trim();
            let data = {
                video_style: document.getElementById('commonVideoStyle').value,
                video_duration: parseInt(document.getElementById('commonDuration').value),
                custom_prompt: customPrompt || null
            };
            
            // Check active tab and add appropriate source
            if (activeTab === 'url') {
                const url = document.getElementById('githubUrl').value;
                if (!url) {
                    alert('Lütfen bir web sitesi URL girin');
                    return;
                }
                
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    alert('Lütfen geçerli bir URL girin (http:// veya https:// ile başlamalı)');
                    return;
                }
                
                currentVideoUrl = url;
                data.url = url;
            } else {
                // Document tab
                if (!uploadedDocumentId) {
                    alert('Lütfen önce bir doküman yükleyin');
                    return;
                }
                
                currentVideoUrl = null;
                data.document_id = uploadedDocumentId;
            }
            
            // Show script preview panel
            document.getElementById('scriptPreview').classList.remove('hidden');
            document.getElementById('scriptLoading').classList.remove('hidden');
            document.getElementById('scriptContent').classList.add('hidden');
            
            try {
                const response = await fetch('/api/scripts/preview', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                currentScript = result.script;
                
                // Show script for editing
                document.getElementById('scriptText').value = currentScript;
                document.getElementById('scriptLoading').classList.add('hidden');
                document.getElementById('scriptContent').classList.remove('hidden');
                
            } catch (error) {
                alert('Script oluşturulamadı: ' + error.message);
                document.getElementById('scriptPreview').classList.add('hidden');
            }
        };
        
        console.log('✅ window.previewScript DEFINED! Type:', typeof window.previewScript);
        
        window.cancelScript = function() {
            document.getElementById('scriptPreview').classList.add('hidden');
            currentScript = null;
        };
        
        window.approveScript = async function() {
            const editedScript = document.getElementById('scriptText').value;
            if (!editedScript) {
                alert('Script eksik');
                return;
            }
            
            // Check source based on active tab
            if (activeTab === 'url' && !currentVideoUrl) {
                alert('URL eksik');
                return;
            }
            if (activeTab === 'document' && !uploadedDocumentId) {
                alert('Doküman eksik');
                return;
            }
            
            const mode = document.getElementById('videoMode').value;
            const customPrompt = document.getElementById('customPrompt').value.trim();
            
            // Check if photo is uploaded for custom_avatar_overlay mode or avatar mode with photo
            let customAvatarImageId = null;
            if (mode === 'custom_avatar_overlay') {
                if (!uploadedPhotoId) {
                    alert('Lütfen önce bir fotoğraf yükleyin!');
                    return;
                }
                customAvatarImageId = uploadedPhotoId;
            } else if (mode === 'avatar' && uploadedPhotoId) {
                // Avatar mode also supports custom photos
                customAvatarImageId = uploadedPhotoId;
            }
            
            // Determine provider: force D-ID if custom avatar, otherwise use selected
            let provider;
            if (customAvatarImageId) {
                provider = 'did';  // Custom avatars require D-ID
            } else if (mode === 'avatar') {
                provider = document.getElementById('provider').value;
            } else {
                provider = 'heygen';
            }
            
            const data = {
                script: editedScript,
                mode: mode,
                scroll_speed: document.getElementById('scrollSpeed').value,
                avatar_type: mode === 'avatar' ? document.getElementById('avatarType').value : 'professional_female',
                voice_type: document.getElementById('commonVoiceType').value,
                video_style: document.getElementById('commonVideoStyle').value,
                provider: provider,
                video_duration: parseInt(document.getElementById('commonDuration').value),
                custom_prompt: customPrompt || null,
                custom_avatar_image_id: customAvatarImageId
            };
            
            // Add URL or document_id based on active tab
            if (activeTab === 'url') {
                data.url = currentVideoUrl;
            } else {
                data.document_id = uploadedDocumentId;
            }
            
            try {
                const response = await fetch('/api/videos/create-with-script', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Video oluşturulamadı');
                }
                
                const result = await response.json();
                currentVideoId = result.video_id;
                
                // Hide script preview and show video status
                document.getElementById('scriptPreview').classList.add('hidden');
                document.getElementById('videoStatus').classList.remove('hidden');
                document.getElementById('videoResult').classList.add('hidden');
                document.getElementById('errorResult').classList.add('hidden');
                document.getElementById('editOptions').classList.add('hidden');
                
                statusInterval = setInterval(checkStatus, 2000);
                
            } catch (error) {
                alert('Hata: ' + error.message);
            }
        };
        
        window.downloadVideo = function() {
            if (!currentVideoId) {
                alert('Video ID bulunamadı');
                return;
            }
            
            const downloadUrl = `/api/videos/${currentVideoId}/download`;
            
            // Create temporary link and trigger download
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `video_${currentVideoId}.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };
        
        window.createVideo = async function() {
            // Check source based on active tab
            if (activeTab === 'url') {
                const url = document.getElementById('githubUrl').value;
                if (!url) {
                    alert('Lütfen bir web sitesi URL girin');
                    return;
                }
                
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    alert('Lütfen geçerli bir URL girin (http:// veya https:// ile başlamalı)');
                    return;
                }
                
                currentVideoUrl = url;
            } else {
                // Document tab
                if (!uploadedDocumentId) {
                    alert('Lütfen önce bir doküman yükleyin');
                    return;
                }
                currentVideoUrl = null;
            }
            
            const mode = document.getElementById('videoMode').value;
            
            // Check if photo is uploaded for custom_avatar_overlay mode or avatar mode with photo
            let customAvatarImageId = null;
            if (mode === 'custom_avatar_overlay') {
                if (!uploadedPhotoId) {
                    alert('Lütfen önce bir fotoğraf yükleyin!');
                    return;
                }
                customAvatarImageId = uploadedPhotoId;
            } else if (mode === 'avatar' && uploadedPhotoId) {
                // Avatar mode also supports custom photos
                customAvatarImageId = uploadedPhotoId;
            }
            
            // Determine provider: force D-ID if custom avatar, otherwise use selected
            let provider;
            if (customAvatarImageId) {
                provider = 'did';  // Custom avatars require D-ID
            } else if (mode === 'avatar') {
                provider = document.getElementById('provider').value;
            } else {
                provider = 'heygen';
            }
            
            const data = {
                mode: mode,
                scroll_speed: document.getElementById('scrollSpeed').value,
                avatar_type: mode === 'avatar' ? document.getElementById('avatarType').value : 'professional_female',
                voice_type: document.getElementById('commonVoiceType').value,
                video_style: document.getElementById('commonVideoStyle').value,
                provider: provider,
                video_duration: parseInt(document.getElementById('commonDuration').value),
                custom_avatar_image_id: customAvatarImageId
            };
            
            // Add URL or document_id based on active tab
            if (activeTab === 'url') {
                data.url = currentVideoUrl;
            } else {
                data.document_id = uploadedDocumentId;
            }
            
            try {
                const response = await fetch('/api/videos/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                currentVideoId = result.video_id;
                
                document.getElementById('videoStatus').classList.remove('hidden');
                document.getElementById('videoResult').classList.add('hidden');
                document.getElementById('errorResult').classList.add('hidden');
                document.getElementById('editOptions').classList.add('hidden');
                
                statusInterval = setInterval(checkStatus, 2000);
                
            } catch (error) {
                alert('Hata: ' + error.message);
            }
        };
        
        window.checkStatus = async function() {
            if (!currentVideoId) return;
            
            try {
                const response = await fetch(`/api/videos/${currentVideoId}/status`);
                const status = await response.json();
                
                document.getElementById('progressBar').style.width = status.progress + '%';
                document.getElementById('progressPercent').textContent = status.progress + '%';
                document.getElementById('statusText').textContent = status.current_stage;
                
                if (status.status === 'completed') {
                    clearInterval(statusInterval);
                    document.getElementById('videoResult').classList.remove('hidden');
                    
                    // Set video player source (streaming endpoint for inline playback)
                    const streamUrl = `/api/videos/${currentVideoId}/stream`;
                    document.getElementById('videoSource').src = streamUrl;
                    document.getElementById('videoPlayer').load();
                    
                    // Set download link (download endpoint with attachment header)
                    const downloadUrl = `/api/videos/${currentVideoId}/download`;
                    document.getElementById('downloadLink').href = downloadUrl;
                    
                } else if (status.status === 'failed') {
                    clearInterval(statusInterval);
                    document.getElementById('errorResult').classList.remove('hidden');
                    document.getElementById('errorText').textContent = '❌ ' + (status.error || 'Bilinmeyen hata');
                }
            } catch (error) {
                console.error('Status check error:', error);
            }
        };
        
        window.toggleEditOptions = function() {
            const editOptions = document.getElementById('editOptions');
            if (editOptions.classList.contains('hidden')) {
                editOptions.classList.remove('hidden');
                
                // Set current values in edit fields
                document.getElementById('editVideoDuration').value = document.getElementById('videoDuration').value;
                document.getElementById('editProvider').value = document.getElementById('provider').value;
                document.getElementById('editAvatarType').value = document.getElementById('avatarType').value;
                document.getElementById('editVoiceType').value = document.getElementById('voiceType').value;
                document.getElementById('editVideoStyle').value = document.getElementById('videoStyle').value;
            } else {
                editOptions.classList.add('hidden');
            }
        };
        
        window.recreateVideo = async function() {
            if (!currentVideoUrl) {
                alert('URL bilgisi bulunamadı');
                return;
            }
            
            // Hide edit options
            document.getElementById('editOptions').classList.add('hidden');
            document.getElementById('videoResult').classList.add('hidden');
            
            // Get new values from edit fields
            const data = {
                url: currentVideoUrl,
                avatar_type: document.getElementById('editAvatarType').value,
                voice_type: document.getElementById('editVoiceType').value,
                video_style: document.getElementById('editVideoStyle').value,
                provider: document.getElementById('editProvider').value,
                video_duration: parseInt(document.getElementById('editVideoDuration').value)
            };
            
            try {
                const response = await fetch('/api/videos/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                currentVideoId = result.video_id;
                
                document.getElementById('videoStatus').classList.remove('hidden');
                document.getElementById('errorResult').classList.add('hidden');
                
                // Reset progress
                document.getElementById('progressBar').style.width = '0%';
                document.getElementById('progressPercent').textContent = '0%';
                
                statusInterval = setInterval(checkStatus, 2000);
                
            } catch (error) {
                alert('Hata: ' + error.message);
            }
        };
        
        console.log('✅ All functions defined globally!');
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/scripts/preview", response_model=ScriptPreviewResponse)
async def preview_script(request: ScriptPreviewRequest):
    """Generate script preview without creating video"""
    try:
        from services.website_analyzer import ContentAnalyzer
        
        # Analyze content based on source type
        if request.url:
            # URL-based content
            content_data = await ContentAnalyzer.analyze_url(str(request.url))
            source = str(request.url)
            source_type = content_data.get("type", "url")
        elif request.document_id:
            # Document-based content
            doc_path = Path("videos/uploads/documents")
            doc_files = list(doc_path.glob(f"{request.document_id}.*"))
            if not doc_files:
                raise HTTPException(status_code=404, detail="Doküman bulunamadı")
            
            doc_file = doc_files[0]
            content_data = await ContentAnalyzer.analyze_document(str(doc_file), doc_file.name)
            source = content_data.get("title", doc_file.name)
            source_type = "document"
        else:
            raise HTTPException(status_code=400, detail="URL veya document_id gerekli")
        
        # Generate script using ScriptGenerator
        script_dict = await ScriptGenerator.generate_script(
            content_data,
            request.video_style,
            request.video_duration,
            custom_prompt=request.custom_prompt or ""
        )
        
        # Extract full_text from dict
        script_text = script_dict.get("full_text", str(script_dict))
        
        return ScriptPreviewResponse(
            script=script_text,
            source=source,
            source_type=source_type,
            video_duration=request.video_duration
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script oluşturulamadı: {str(e)}")

@app.post("/api/uploads/test")
async def test_upload():
    """Simple test endpoint"""
    return {"status": "ok", "message": "Upload endpoint is reachable"}

@app.post("/api/uploads/image")
async def upload_avatar_image(file: UploadFile = File(...)):
    """Upload custom avatar photo for overlay"""
    try:
        print(f"📤 Upload başladı: {file.filename}, content_type: {file.content_type}")
        
        # Validate file type
        if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
            raise HTTPException(status_code=400, detail="Sadece JPG/PNG dosyaları desteklenir")
        
        # Read file content
        print("📖 Dosya okunuyor...")
        content = await file.read()
        print(f"✅ Dosya okundu: {len(content)} bytes")
        
        # Validate file size (max 5MB)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Dosya boyutu 5MB'dan küçük olmalıdır")
        
        # Validate image and get dimensions
        print("🖼️ Resim doğrulanıyor...")
        try:
            # First verify it's a valid image
            img = Image.open(io.BytesIO(content))
            img.verify()
            
            # Re-open to get dimensions (verify() closes the file)
            img = Image.open(io.BytesIO(content))
            width, height = img.size
            print(f"✅ Resim geçerli: {width}x{height}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Geçersiz resim dosyası: {str(e)}")
        
        # Generate unique ID for the image
        image_id = str(uuid.uuid4())
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("videos/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the image
        file_ext = "jpg" if file.content_type == "image/jpeg" else "png"
        file_path = upload_dir / f"{image_id}.{file_ext}"
        
        print(f"💾 Dosya kaydediliyor: {file_path}")
        with open(file_path, "wb") as f:
            f.write(content)
        print("✅ Dosya kaydedildi")
        
        # Don't save to DB for now - just return success
        print(f"✅ Upload tamamlandı: {image_id}")
        return {
            "image_id": image_id,
            "file_path": str(file_path),
            "dimensions": {"width": width, "height": height},
            "message": "Fotoğraf başarıyla yüklendi!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Yükleme hatası: {str(e)}")

@app.post("/api/uploads/document")
async def upload_document(file: UploadFile = File(...)):
    """Upload document (PDF, DOCX, TXT, MD) for video generation"""
    try:
        # Validate filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="Dosya adı gerekli")
        
        print(f"📄 Doküman upload başladı: {file.filename}, content_type: {file.content_type}")
        
        # Check if file format is supported
        if not DocumentAnalyzer.is_supported_document(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Desteklenmeyen dosya formatı. Desteklenen: PDF, DOCX, TXT, MD"
            )
        
        # Read file content
        print("📖 Dosya okunuyor...")
        content = await file.read()
        print(f"✅ Dosya okundu: {len(content)} bytes")
        
        # Validate file size (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Dosya boyutu 10MB'dan küçük olmalıdır")
        
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Create documents upload directory
        upload_dir = Path("videos/uploads/documents")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the document with original extension
        file_ext = Path(file.filename).suffix.lower()
        file_path = upload_dir / f"{doc_id}{file_ext}"
        
        print(f"💾 Doküman kaydediliyor: {file_path}")
        with open(file_path, "wb") as f:
            f.write(content)
        print("✅ Doküman kaydedildi")
        
        # Analyze document to extract content
        print("📊 İçerik analiz ediliyor...")
        analysis_result = await DocumentAnalyzer.analyze_document(str(file_path), file.filename)
        print(f"✅ İçerik analiz edildi: {analysis_result['word_count']} kelime")
        
        # Check if content was truncated
        truncated = analysis_result.get('truncated', False)
        message = "Doküman başarıyla yüklendi ve analiz edildi!"
        if truncated:
            message = f"⚠️ Doküman yüklendi ancak {analysis_result.get('original_length')} karakterden {10000} karaktere kısaltıldı. Tam içerik video'da kullanılmayabilir."
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_type": analysis_result['file_type'],
            "title": analysis_result['title'],
            "word_count": analysis_result['word_count'],
            "content_preview": analysis_result['content'][:200] + "..." if len(analysis_result['content']) > 200 else analysis_result['content'],
            "truncated": truncated,
            "original_length": analysis_result.get('original_length'),
            "message": message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Doküman upload hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Doküman yükleme hatası: {str(e)}")

@app.post("/api/videos/create")
async def create_video(request: VideoCreateRequest, background_tasks: BackgroundTasks):
    """Create a new video generation task"""
    video_id = str(uuid.uuid4())
    
    videos_db[video_id] = {
        "video_id": video_id,
        "status": "processing",
        "progress": 0,
        "current_stage": "Initializing...",
        "video_url": None,
        "youtube_url": None,
        "created_at": None,
        "completed_at": None,
        "error": None
    }
    
    await save_videos_db(videos_db)  # Save new video to disk
    background_tasks.add_task(process_video_pipeline, video_id, request)
    
    return {"video_id": video_id, "status": "processing"}

@app.post("/api/videos/create-with-script")
async def create_video_with_script(request: VideoCreateWithScriptRequest, background_tasks: BackgroundTasks):
    """Create a new video with pre-approved script"""
    video_id = str(uuid.uuid4())
    
    videos_db[video_id] = {
        "video_id": video_id,
        "status": "processing",
        "progress": 0,
        "current_stage": "Initializing...",
        "video_url": None,
        "youtube_url": None,
        "created_at": None,
        "completed_at": None,
        "error": None,
        "approved_script": request.script  # Store the approved script
    }
    
    await save_videos_db(videos_db)
    background_tasks.add_task(process_video_pipeline_with_script, video_id, request)
    
    return {"video_id": video_id, "status": "processing"}

@app.get("/api/videos/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """Get video processing status"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return videos_db[video_id]

@app.get("/api/videos/{video_id}/stream")
async def stream_video(video_id: str):
    """Stream video for inline playback in browser"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = videos_db[video_id]
    if video["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready")
    
    video_path = video.get("video_path", f"videos/final_{video_id}.mp4")
    
    if not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        headers={
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes"
        }
    )

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio file for D-ID API"""
    audio_path = f"videos/{filename}"
    
    if not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg"
    )

@app.get("/api/videos/{video_id}/download")
async def download_video(video_id: str):
    """Download completed video"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = videos_db[video_id]
    if video["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready")
    
    video_path = video.get("video_path", f"videos/final_{video_id}.mp4")
    
    if not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Force download with proper headers
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"video_{video_id}.mp4",
        headers={
            "Content-Disposition": f"attachment; filename=video_{video_id}.mp4"
        }
    )

@app.get("/api/status")
async def get_api_status():
    """Check status of all API services"""
    status = {}
    
    # Check OpenAI
    from services.ai_service import AIService
    ai_service = AIService()
    status["openai"] = {
        "enabled": ai_service.provider == "openai",
        "api_key_present": bool(ai_service.openai_key)
    }
    
    # Check Anthropic
    status["anthropic"] = {
        "enabled": ai_service.provider == "anthropic",
        "api_key_present": bool(ai_service.anthropic_key)
    }
    
    # Check ElevenLabs
    from services.elevenlabs_service import ElevenLabsService
    elevenlabs = ElevenLabsService()
    status["elevenlabs"] = {
        "enabled": elevenlabs.enabled,
        "api_key_present": bool(elevenlabs.api_key),
        "note": "Quota may be limited - only 2204 credits remaining"
    }
    
    # Check HeyGen
    from services.heygen_service import HeyGenService
    heygen = HeyGenService()
    status["heygen"] = {
        "enabled": heygen.enabled,
        "api_key_present": bool(heygen.api_key),
        "avatars_available": len(heygen.avatars),
        "note": "Service enabled but may have issues creating videos"
    }
    
    # Check D-ID (optional service)
    try:
        from services.did_service import DIDService
        did = DIDService()
        status["did"] = {
            "enabled": did.enabled,
            "api_key_present": bool(getattr(did, 'api_key', None))
        }
    except Exception as e:
        print(f"⚠️ Could not load D-ID service: {str(e)}")
        status["did"] = {
            "enabled": False,
            "api_key_present": False,
            "note": "Service not configured"
        }
    
    # Overall status
    status["overall"] = {
        "ai_available": status["openai"]["enabled"] or status["anthropic"]["enabled"],
        "tts_available": status["elevenlabs"]["enabled"],
        "avatar_available": status["heygen"]["enabled"] or status.get("did", {}).get("enabled", False),
        "ready": ((status["openai"]["enabled"] or status["anthropic"]["enabled"]) and 
                  status["elevenlabs"]["enabled"] and 
                  (status["heygen"]["enabled"] or status.get("did", {}).get("enabled", False)))
    }
    
    return status

@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404 errors"""
    # Return a minimal valid ICO file (16x16 transparent)
    ico_bytes = bytes([
        0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x10, 0x10,
        0x00, 0x00, 0x01, 0x00, 0x20, 0x00, 0x68, 0x04,
        0x00, 0x00, 0x16, 0x00, 0x00, 0x00
    ])
    return Response(content=ico_bytes, media_type="image/x-icon")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
