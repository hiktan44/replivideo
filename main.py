"""
AI Avatar Video Maker - Replit Complete Application
Generates 10-minute Turkish tutorial videos from GitHub repositories
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
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

videos_db = {}

class VideoCreateRequest(BaseModel):
    url: HttpUrl
    avatar_type: str = "professional_female"
    voice_type: str = "tr_female_professional"
    video_style: str = "tutorial"
    provider: str = "heygen"  # "did" or "heygen"

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

class GitHubAnalyzer:
    """GitHub repository analysis service"""
    
    @staticmethod
    async def analyze_repo(url: str) -> Dict:
        """Extract GitHub repository information"""
        try:
            parts = url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
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
                except:
                    pass
                
                languages = {}
                try:
                    lang_url = f"https://api.github.com/repos/{owner}/{repo_name}/languages"
                    lang_response = await client.get(lang_url)
                    languages = lang_response.json()
                except:
                    pass
                
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
    async def generate_script(repo_data: Dict, style: str) -> Dict:
        """Generate 10-minute Turkish video script using AI"""
        
        from services.ai_service import AIService
        
        ai_service = AIService()
        script_text = await ai_service.generate_turkish_script(repo_data, style)
        
        sections = []
        current_section = None
        
        for line in script_text.strip().split('\n'):
            if line.startswith('['):
                if current_section:
                    sections.append(current_section)
                
                timestamp = line.split(']')[0].replace('[', '')
                title = line.split(']')[1].strip() if ']' in line else ""
                
                # All sections are avatar-based for video generation
                section_type = "avatar"
                
                current_section = {
                    "timestamp": timestamp,
                    "title": title,
                    "type": section_type,
                    "text": ""
                }
            elif current_section and line.strip():
                current_section["text"] += line + "\n"
        
        if current_section:
            sections.append(current_section)
        
        return {
            "full_text": script_text,
            "sections": sections,
            "metadata": {
                "word_count": len(script_text.split()),
                "estimated_duration": "10:00",
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

def update_progress(video_id: str, progress: int, stage: str):
    """Update video processing progress"""
    if video_id in videos_db:
        videos_db[video_id]["progress"] = progress
        videos_db[video_id]["current_stage"] = stage

async def process_video_pipeline(video_id: str, request: VideoCreateRequest):
    """Main video generation pipeline"""
    try:
        videos_db[video_id]["created_at"] = datetime.now().isoformat()
        
        update_progress(video_id, 10, "📊 Analyzing content...")
        await asyncio.sleep(1)
        
        from services.website_analyzer import ContentAnalyzer
        repo_data = await ContentAnalyzer.analyze_url(str(request.url))
        
        update_progress(video_id, 25, "✍️ Generating 10-minute Turkish script with AI...")
        script = await ScriptGenerator.generate_script(repo_data, request.video_style)
        
        update_progress(video_id, 45, "🎤 Creating Turkish professional voiceover...")
        audio_file = await TTSService.generate_audio(script, request.voice_type)
        
        update_progress(video_id, 65, f"🎭 Rendering avatar video segments with {request.provider.upper()}...")
        avatar_videos = await AvatarService.render_avatar_segments(script, request.avatar_type, audio_file, request.provider)
        
        update_progress(video_id, 85, "🎬 Composing final video...")
        
        from services.video_composer import VideoComposer
        composer = VideoComposer()
        final_video = await composer.compose_video(avatar_videos, audio_file, video_id)
        
        update_progress(video_id, 100, "✅ Video completed successfully!")
        videos_db[video_id]["status"] = "completed"
        videos_db[video_id]["video_url"] = f"/api/videos/{video_id}/download"
        videos_db[video_id]["video_path"] = final_video
        videos_db[video_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        videos_db[video_id]["status"] = "failed"
        videos_db[video_id]["error"] = str(e)
        videos_db[video_id]["current_stage"] = f"❌ Error: {str(e)}"

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
            <p class="text-center text-gray-600 mb-8">Herhangi bir web sitesi veya GitHub projesinden otomatik 10 dakikalık Türkçe eğitim videoları oluşturun</p>
            
            <div class="bg-white rounded-lg shadow-xl p-6 mb-6">
                <h2 class="text-2xl font-semibold mb-4">Yeni Video Oluştur</h2>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Web Sitesi veya GitHub URL</label>
                        <input type="text" id="githubUrl" placeholder="https://example.com veya https://github.com/owner/repo" 
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent">
                        <p class="text-xs text-gray-500 mt-1">✨ Herhangi bir web sitesi URL'i girin - otomatik analiz edilecek!</p>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
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
            
            const data = {
                url: url,
                avatar_type: document.getElementById('avatarType').value,
                voice_type: document.getElementById('voiceType').value,
                video_style: document.getElementById('videoStyle').value,
                provider: document.getElementById('provider').value
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
                provider: document.getElementById('editProvider').value
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
    
    background_tasks.add_task(process_video_pipeline, video_id, request)
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
