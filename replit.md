# AI Avatar Video Maker

## Overview

AI Avatar Video Maker is a FastAPI-based web application that automatically generates Turkish tutorial videos (5, 10, or 15 minutes) from **any website or GitHub repository**. The system analyzes web content, generates professional Turkish scripts using AI, creates voiceovers, and combines them with AI avatar videos or screen recordings to produce complete educational content.

The application provides a REST API and web interface for submitting any web URL (including GitHub repositories) and monitoring video creation progress in real-time. Users can also **upload their own photo to create a personalized talking avatar** that appears in a circular frame at the video corner with lip-sync and facial expressions.

## Recent Changes (October 2025)

**NEW: Custom Photo Avatar Overlay** (Latest - Oct 10):
- ✅ Implemented custom photo upload feature - users can upload their own photo to create personalized talking avatar
- ✅ Added `/api/uploads/image` endpoint with image validation (5MB max, JPG/PNG only)
- ✅ Extended DIDService to support custom images via base64 encoding for D-ID API
- ✅ Implemented FFmpeg circular mask overlay in VideoComposer for professional circular avatar display
- ✅ Added `custom_avatar_overlay` video mode combining screen recording + custom photo avatar
- ✅ Avatar displayed in circular frame at video corner (bottom-right) with lip-sync and facial expressions
- ✅ Frontend photo preview and upload integration in both direct video creation and script preview flows
- ✅ Installed python-multipart for file upload support
- ✅ **User Experience**: Upload your photo, it talks and appears in a circular frame at video corner!

**Script Preview & Editing** (Oct 10):
- ✅ Implemented script preview workflow - users can review AI-generated scripts before video creation
- ✅ Added `/api/scripts/preview` endpoint for generating scripts without creating videos
- ✅ Added `/api/videos/create-with-script` endpoint for creating videos with pre-approved scripts
- ✅ Removed section headers from scripts for natural conversational flow
- ✅ Updated AI prompts to generate seamless, natural Turkish narration without timestamps or section markers
- ✅ Enhanced frontend with script preview panel, textarea editing, and approve/cancel buttons
- ✅ Added sub-page navigation to ScreenRecorderService - automatically clicks internal links
- ✅ Fixed download button to trigger immediate file download (onclick method)
- ✅ **NEW: Custom Prompt Feature** - Users can add specific instructions via textarea input
- ✅ Custom prompts integrated into AI script generation for personalized video content
- ✅ Both script preview and video creation endpoints support custom_prompt parameter
- ✅ **User Experience**: Full control over script content before video generation starts

**Screen Recording Mode** (Oct 10):
- ✅ Implemented Playwright-based browser automation for fast video generation
- ✅ Created `ScreenRecorderService` with automated web navigation and scrolling
- ✅ Added Nix Chromium integration (bypasses Playwright's bundled browser dependency issues)
- ✅ Installed system dependencies: mesa, X11 libs, NSS, GTK3, alsa-lib for browser support
- ✅ Extended `VideoComposer` with screen recording audio muxing (webm→mp4 conversion)
- ✅ Updated API with "mode" parameter: "avatar" (slow, AI avatar) vs "screen_recording" (fast, real webpage)
- ✅ Enhanced frontend UI with mode selection and scroll speed control
- ✅ **Performance**: Screen recording mode generates 10-min video in ~5 minutes (vs 30-60 min for avatar mode)
- ✅ Set `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true` for Nix environment compatibility

**Critical Bug Fixes** (Oct 9):
- ✅ Fixed GitHub URL parsing to properly handle `.git` suffix (only removes from end, not from repo names)
- ✅ Increased HeyGen timeout from 2 to 5 minutes to prevent premature timeouts
- ✅ Added fallback for script parsing when AI doesn't generate sections
- ✅ Implemented thread safety with asyncio.Lock for videos_db concurrent access
- ✅ Sanitized error messages to prevent sensitive information disclosure
- ✅ Fixed all bare exception handlers with specific exception types
- ✅ Added favicon route to eliminate 404 errors
- ✅ Made all save_videos_db calls properly async with await

**FFmpeg Video Composition** (Oct 9):
- ✅ Implemented real video composition using FFmpeg
- ✅ Fixed ElevenLabs async generator bug (removed incorrect await)
- ✅ Fixed AI service f-string backslash syntax errors (used chr(39) for apostrophes)
- ✅ Videos now properly concatenate D-ID avatar clips with ElevenLabs audio
- ✅ Added QuickTime compatibility with `-movflags +faststart`
- ✅ Installed FFmpeg system dependency
- ✅ Real MP4 files now generated instead of text placeholders

**Web Content Expansion**:
- Added `WebsiteAnalyzer` service for general web scraping using BeautifulSoup
- Added `ContentAnalyzer` unified router that auto-detects URL type (GitHub vs general website)
- Updated AI prompts to generate appropriate scripts for both GitHub repos and general websites
- Enhanced frontend to accept any web URL with automatic content type detection
- Maintains backward compatibility with existing GitHub repository analysis

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
1. **Content analysis** - Auto-detects and analyzes GitHub repos OR general websites
2. AI script generation (10-minute Turkish tutorial)
3. Text-to-speech audio generation
4. Avatar video creation with lip-sync
5. Video composition and finalization

**Service Layer Architecture**: Modular service-based design
- `GitHubAnalyzer`: Repository content extraction and analysis (GitHub-specific)
- `WebsiteAnalyzer`: General web content extraction using BeautifulSoup
- `ContentAnalyzer`: Unified router that auto-detects URL type and delegates to appropriate analyzer
- `AIService`: Script generation using OpenAI or Anthropic (supports both GitHub and website content)
- `ElevenLabsService`: Turkish text-to-speech conversion
- `ScreenRecorderService`: Playwright-based browser automation for screen recording (NEW - Oct 10)
- `HeyGenService`: AI avatar video generation with HeyGen
- `DIDService`: AI avatar video generation with D-ID
- `VideoComposer`: Final video assembly and composition (supports both avatar and screen recording modes)

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

**Primary Storage**: Persistent JSON file with in-memory cache (`videos_db`)
- Video metadata: ID, status, progress, timestamps
- Progress tracking: current stage, completion percentage
- Results: video URLs, YouTube URLs (future feature)
- Thread-safe access using asyncio.Lock for concurrent operations
- Automatic persistence to `videos_db.json` file
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
- **Dual content type support**:
  - **GitHub repos**: Integrates repository metadata (stars, forks, language, README)
  - **General websites**: Extracts title, description, headings, main content, and links
- Dynamic prompt generation based on content type

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

**Composition Strategy**: FFmpeg-based VideoComposer service
- **Real video composition using FFmpeg** (implemented Oct 9, 2025)
- Concatenates D-ID avatar clips using FFmpeg concat demuxer
- Muxes ElevenLabs narration audio with AAC encoding
- QuickTime compatibility via `-movflags +faststart`
- Async subprocess execution to keep service responsive
- Graceful fallback to demo mode if FFmpeg fails
- Automatic temp file cleanup after composition

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
- Used for GitHub API, avatar services, and web scraping

**BeautifulSoup4**: HTML parsing (NEW)
- Web content extraction from any URL
- HTML parsing and cleaning
- Main content identification and extraction

**Python Environment**: UV package manager
- Dependency management via `uv sync`
- Environment-based configuration

**FFmpeg**: Video composition system dependency (NEW - Oct 9, 2025)
- System package: `ffmpeg-full` installed via Nix
- Used for concatenating D-ID avatar video clips
- Muxes ElevenLabs audio with video streams
- Provides QuickTime compatibility with movflags
- Async subprocess execution for non-blocking operations

### Content Source Integration

**GitHub API**: Repository analysis (when GitHub URL detected)
- Public API access (no authentication for public repos)
- Extracts: README, languages, stars, forks, topics, license
- No dedicated API key required for public repositories

**Web Scraping**: General website analysis (NEW - when non-GitHub URL detected)
- Uses BeautifulSoup4 for HTML parsing
- Extracts: title, meta description, headings, main content, links
- Automatic content area detection (main, article, content divs)
- Removes navigation, scripts, and style elements for clean content

### Future Integration Points

**YouTube**: Video upload capability
- Mentioned in data models (`youtube_url` field)
- Not yet implemented
- Would require YouTube Data API credentials