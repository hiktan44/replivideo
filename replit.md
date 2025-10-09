# AI Avatar Video Maker

## Overview

AI Avatar Video Maker is a FastAPI-based web application that automatically generates 10-minute Turkish tutorial videos from GitHub repositories. The system analyzes repository content, generates professional Turkish scripts using AI, creates voiceovers, and combines them with AI avatar videos to produce complete educational content.

The application provides a REST API and web interface for submitting GitHub URLs and monitoring video creation progress in real-time.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture

**Framework**: FastAPI
- RESTful API with async/await patterns for concurrent operations
- CORS middleware enabled for cross-origin requests
- Background task processing for video generation pipeline
- In-memory database (`videos_db` dictionary) for storing video metadata and status

**Video Generation Pipeline**: Multi-stage asynchronous workflow
1. GitHub repository analysis and content extraction
2. AI script generation (10-minute Turkish tutorial)
3. Text-to-speech audio generation
4. Avatar video creation with lip-sync
5. Video composition and finalization

**Service Layer Architecture**: Modular service-based design
- `GitHubAnalyzer`: Repository content extraction and analysis
- `AIService`: Script generation using OpenAI or Anthropic
- `ElevenLabsService`: Turkish text-to-speech conversion
- `DIDService`: AI avatar video generation with D-ID
- `VideoComposer`: Final video assembly and composition

**Graceful Degradation**: Demo mode fallbacks when API keys are unavailable
- Each service checks for API key availability on initialization
- Falls back to demo/placeholder content when keys are missing
- Allows development and testing without all API credentials

### Frontend Architecture

**Interface**: Simple web UI served via FastAPI
- HTML/JavaScript-based interface
- Real-time progress tracking via polling or WebSocket
- Static file serving for videos and assets
- File download capability for generated videos

### Data Storage

**Primary Storage**: In-memory dictionary (`videos_db`)
- Video metadata: ID, status, progress, timestamps
- Progress tracking: current stage, completion percentage
- Results: video URLs, YouTube URLs (future feature)
- Error state management

**File Storage**: Local filesystem
- Video outputs stored in `videos/` directory
- Demo assets stored in `demo_assets/` directory
- Generated audio files: `videos/audio_{voice_type}.mp3`
- Final videos: `videos/final_{video_id}.mp4`

**Future Enhancement Consideration**: Comment suggests migration to Replit DB for persistence

### Authentication & Authorization

**Current Implementation**: No authentication
- Public API endpoints
- Open access for MVP/demo purposes

**API Key Management**: Environment variable based
- Service-level API key validation
- Keys stored in `.env` file
- Separate keys for each external service

### Video Processing Architecture

**Script Generation Strategy**: AI-powered content creation
- Bilingual support: OpenAI or Anthropic as providers
- Turkish language optimization
- Structured prompt engineering for 10-minute video format (1500-1800 words)
- Repository metadata integration (stars, forks, language, README)

**Audio Generation Strategy**: Professional Turkish voiceovers
- ElevenLabs multilingual v2 model
- Multiple voice options (professional/friendly, male/female)
- MP3 output at 44.1kHz, 128kbps
- Text truncation at 5000 characters for API limits

**Avatar Video Strategy**: D-ID lip-sync technology
- Pre-configured avatar image URLs for different personas
- Microsoft Azure neural voices for Turkish (tr-TR-EmelNeural)
- Text truncation at 500 characters per clip
- Multiple avatar types: professional/casual, male/female

**Composition Strategy**: Implemented VideoComposer service
- Creates valid MP4 files for demo mode
- Properly awaits video composition and stores file path
- Future enhancement: FFmpeg integration for real video composition
- Combines multiple avatar clips with audio track

## External Dependencies

### AI & ML Services

**OpenAI** (Optional - Script Generation)
- API: OpenAI GPT models via AsyncOpenAI client
- Purpose: Turkish tutorial script generation
- Configuration: `OPENAI_API_KEY` environment variable
- Fallback: Anthropic or demo mode

**Anthropic** (Optional - Script Generation)
- API: Claude models via AsyncAnthropic client  
- Purpose: Alternative AI script generation
- Configuration: `ANTHROPIC_API_KEY` environment variable
- Fallback: OpenAI or demo mode

**ElevenLabs** (Text-to-Speech)
- API: ElevenLabs TTS API with AsyncElevenLabs client
- Purpose: Turkish language audio generation
- Model: eleven_multilingual_v2
- Voice IDs: Mapped to Turkish neural voices
- Configuration: `ELEVENLABS_API_KEY` environment variable
- Output: MP3 format (44.1kHz, 128kbps)

**D-ID** (Avatar Generation)
- API: D-ID talking avatar API
- Purpose: Lip-synced avatar video creation
- Integration: Microsoft Azure TTS (tr-TR-EmelNeural)
- Configuration: `DID_API_KEY` environment variable
- Avatar sources: Pre-configured S3 bucket URLs

### Core Dependencies

**FastAPI**: Web framework
- Async request handling
- Pydantic data validation
- OpenAPI documentation
- CORS middleware support

**httpx**: HTTP client
- Async API calls to external services
- Used for GitHub API and avatar services

**Python Environment**: UV package manager
- Dependency management via `uv sync`
- Environment-based configuration

### GitHub Integration

**GitHub API**: Repository analysis
- Public API access (no authentication for public repos)
- Extracts: README, languages, stars, forks, topics, license
- No dedicated API key required for public repositories

### Future Integration Points

**YouTube**: Video upload capability
- Mentioned in data models (`youtube_url` field)
- Not yet implemented
- Would require YouTube Data API credentials

**FFmpeg**: Video composition
- Currently placeholder/demo mode
- Required for real video assembly
- Combines avatar clips with audio tracks
- Not yet integrated in codebase