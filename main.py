"""
AI Avatar Video Maker - Replit Complete Application
Generates 10-minute Turkish tutorial videos from GitHub repositories
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List
import os
import uuid
import json
import asyncio
from datetime import datetime
import httpx
import base64
from pathlib import Path

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
    url: HttpUrl
    avatar_type: str = "professional_female"
    voice_type: str = "tr_female_professional"
    video_style: str = "tutorial"
    provider: str = "heygen"  # "did" or "heygen"
    video_duration: int = 10  # 5, 10, or 15 minutes
    mode: str = "avatar"  # "avatar" or "screen_recording"
    scroll_speed: str = "medium"  # For screen recording: "slow", "medium", "fast"

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
    url: HttpUrl
    video_style: str = "tutorial"
    video_duration: int = 10

class ScriptPreviewResponse(BaseModel):
    script: str
    url: str
    video_duration: int

class VideoCreateWithScriptRequest(BaseModel):
    url: HttpUrl
    script: str
    avatar_type: str = "professional_female"
    voice_type: str = "tr_female_professional"
    video_style: str = "tutorial"
    provider: str = "heygen"
    video_duration: int = 10
    mode: str = "avatar"
    scroll_speed: str = "medium"

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
    async def generate_script(repo_data: Dict, style: str, video_duration: int = 10) -> Dict:
        """Generate Turkish video script using AI based on duration
        
        Args:
            repo_data: Content/repository data
            style: Video style (tutorial, review, quick_start)
            video_duration: Video duration in minutes (5, 10, or 15)
        """
        
        from services.ai_service import AIService
        
        ai_service = AIService()
        script_text = await ai_service.generate_turkish_script(repo_data, style, video_duration)
        
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
    async def generate_audio(script: Dict, voice_type: str) -> str:
        """Generate Turkish audio using ElevenLabs"""
        
        from services.elevenlabs_service import ElevenLabsService
        
        elevenlabs = ElevenLabsService()
        audio_path = await elevenlabs.text_to_speech(script["full_text"], voice_type)
        
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
        
        if request.mode == "screen_recording":
            await update_progress(video_id, 10, "📊 Preparing screen recording...")
            
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            screen_video = await recorder.record_website(
                url=str(request.url),
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
            
            await update_progress(video_id, 50, f"🎭 Rendering avatar video segments with {request.provider.upper()}...")
            avatar_videos = await AvatarService.render_avatar_segments(script, request.avatar_type, audio_file, request.provider)
            
            await update_progress(video_id, 75, "🎬 Composing final video...")
            from services.video_composer import VideoComposer
            composer = VideoComposer()
            final_video = await composer.compose_video(avatar_videos, audio_file, video_id)
            
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
        
        # Check mode: screen_recording or avatar
        if request.mode == "screen_recording":
            # Screen recording pipeline (FAST!)
            await update_progress(video_id, 10, "📊 Analyzing content...")
            await asyncio.sleep(1)
            
            from services.website_analyzer import ContentAnalyzer
            repo_data = await ContentAnalyzer.analyze_url(str(request.url))
            
            await update_progress(video_id, 20, f"🎬 Recording screen with browser automation...")
            from services.screen_recorder import ScreenRecorderService
            recorder = ScreenRecorderService()
            screen_video = await recorder.record_website(
                url=str(request.url),
                video_id=video_id,
                duration_minutes=request.video_duration,
                scroll_speed=request.scroll_speed
            )
            
            await update_progress(video_id, 50, f"✍️ Generating {request.video_duration}-minute Turkish narration script with AI...")
            script = await ScriptGenerator.generate_script(repo_data, request.video_style, request.video_duration)
            
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
            repo_data = await ContentAnalyzer.analyze_url(str(request.url))
            
            await update_progress(video_id, 25, f"✍️ Generating {request.video_duration}-minute Turkish script with AI...")
            script = await ScriptGenerator.generate_script(repo_data, request.video_style, request.video_duration)
            
            await update_progress(video_id, 45, "🎤 Creating Turkish professional voiceover...")
            audio_file = await TTSService.generate_audio(script, request.voice_type)
            
            await update_progress(video_id, 65, f"🎭 Rendering avatar video segments with {request.provider.upper()}...")
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
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Web Sitesi veya GitHub URL</label>
                        <input type="text" id="githubUrl" placeholder="https://example.com veya https://github.com/owner/repo" 
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent">
                        <p class="text-xs text-gray-500 mt-1">✨ Herhangi bir web sitesi URL'i girin - otomatik analiz edilecek!</p>
                    </div>
                    
                    <!-- Video Mode Selection -->
                    <div class="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">🎥 Video Oluşturma Modu</label>
                        <select id="videoMode" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" onchange="toggleModeOptions()">
                            <option value="screen_recording">🚀 Ekran Kaydı (Hızlı - 5 dakika)</option>
                            <option value="avatar">👤 AI Avatar (Yavaş - 30-60 dakika)</option>
                        </select>
                        <p class="text-xs text-blue-600 mt-1">✨ Ekran kaydı modu: Otomatik sayfa gezintisi + AI seslendirme (ÖNERİLEN!)</p>
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
                    
                    <button onclick="createVideo()" 
                            class="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition duration-200">
                        🚀 Video Oluştur
                    </button>
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
                            <a id="downloadLink" href="#" download class="flex-1 bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition text-center">
                                📥 Videoyu İndir
                            </a>
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
        let currentVideoId = null;
        let currentVideoUrl = null;
        let statusInterval = null;
        
        // Check API status on page load
        function toggleModeOptions() {
            const mode = document.getElementById('videoMode').value;
            const avatarOptions = document.getElementById('avatarOptions');
            const scrollSpeedOption = document.getElementById('scrollSpeedOption');
            
            if (mode === 'avatar') {
                avatarOptions.classList.remove('hidden');
                scrollSpeedOption.classList.add('hidden');
            } else {
                avatarOptions.classList.add('hidden');
                scrollSpeedOption.classList.remove('hidden');
            }
        }
        
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
        
        async function createVideo() {
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
            
            const mode = document.getElementById('videoMode').value;
            
            const data = {
                url: url,
                mode: mode,
                scroll_speed: document.getElementById('scrollSpeed').value,
                avatar_type: mode === 'avatar' ? document.getElementById('avatarType').value : 'professional_female',
                voice_type: document.getElementById('commonVoiceType').value,
                video_style: document.getElementById('commonVideoStyle').value,
                provider: mode === 'avatar' ? document.getElementById('provider').value : 'heygen',
                video_duration: parseInt(document.getElementById('commonDuration').value)
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
                document.getElementById('videoResult').classList.add('hidden');
                document.getElementById('errorResult').classList.add('hidden');
                document.getElementById('editOptions').classList.add('hidden');
                
                statusInterval = setInterval(checkStatus, 2000);
                
            } catch (error) {
                alert('Hata: ' + error.message);
            }
        }
        
        async function checkStatus() {
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
        }
        
        function toggleEditOptions() {
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
        }
        
        async function recreateVideo() {
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
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/scripts/preview", response_model=ScriptPreviewResponse)
async def preview_script(request: ScriptPreviewRequest):
    """Generate script preview without creating video"""
    try:
        # Analyze content
        from services.content_analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        content_data = await analyzer.analyze_url(str(request.url))
        
        # Generate script
        from services.ai_service import AIService
        ai_service = AIService()
        script = await ai_service.generate_turkish_script(
            content_data,
            request.video_style,
            request.video_duration
        )
        
        return ScriptPreviewResponse(
            script=script,
            url=str(request.url),
            video_duration=request.video_duration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script oluşturulamadı: {str(e)}")

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
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"github_video_{video_id}.mp4"
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
