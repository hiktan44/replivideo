# AI Avatar Video Maker

## Overview

AI Avatar Video Maker is a FastAPI-based web application that automatically generates Turkish tutorial videos from any website, GitHub repository, or document (PDF/DOCX/TXT/MD). The system analyzes content, generates professional Turkish scripts using AI, creates voiceovers, and combines them with AI avatar videos or screen recordings. Users can also upload their own photo to create a personalized talking avatar with lip-sync and facial expressions, appearing in a circular frame. The project aims to provide an efficient way to produce educational content.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture

The backend is built with FastAPI, providing a RESTful API with async/await patterns for concurrent operations and background task processing for video generation. It utilizes an in-memory database (`videos_db`) for metadata and status, persisted to a JSON file.

The video generation pipeline is a multi-stage asynchronous workflow:
1.  **Content Analysis**: Auto-detects and analyzes content from URLs (GitHub, general websites) or uploaded documents (PDF/DOCX/TXT/MD).
2.  **AI Script Generation**: Creates professional 10-minute Turkish tutorial scripts.
3.  **Text-to-Speech**: Generates audio narration.
4.  **Avatar/Screen Recording**: Creates avatar videos with lip-sync or records website interactions.
5.  **Video Composition**: Finalizes and combines all elements.

Key services include `GitHubAnalyzer`, `WebsiteAnalyzer`, `DocumentAnalyzer`, `ContentAnalyzer`, `AIService` (for script generation), `ElevenLabsService` (for TTS), `DIDService` (for D-ID avatars), `ScreenRecorderService` (Playwright-based screen recording), and `VideoComposer` (FFmpeg-based composition). The architecture includes graceful degradation with demo mode fallbacks when API keys are unavailable.

### Frontend Architecture

A simple web UI, served via FastAPI, provides an HTML/JavaScript-based interface for submitting content, uploading documents/images, and tracking video generation progress. It supports real-time updates and direct video downloads.

### Data Storage

Video metadata and status are stored in an in-memory `videos_db` dictionary, which is persisted to `videos_db.json`. Generated videos, audio files, and temporary assets are stored on the local filesystem in `videos/` and `demo_assets/` directories.

### Authentication & Authorization

Currently, there is no authentication. API keys for external services are managed via environment variables (`.env` file).

### Video Processing Architecture

-   **Script Generation**: AI-powered (OpenAI/Anthropic) in Turkish, optimized for 10-minute tutorials (1500-1800 words). It dynamically adapts prompts based on content type (GitHub repos, websites, or documents) and supports custom user prompts.
-   **Audio Generation**: Utilizes ElevenLabs' multilingual v2 model for professional Turkish voiceovers, generating MP3 files.
-   **Avatar Video**: Employs D-ID lip-sync technology with pre-configured avatar images or user-uploaded photos. Uses Microsoft Azure neural voices for Turkish.
-   **Screen Recording**: Playwright-based browser automation (`ScreenRecorderService`) captures website interactions, significantly speeding up video generation compared to avatar mode.
-   **Video Composition**: FFmpeg-based `VideoComposer` concatenates avatar clips, muxes ElevenLabs audio, and ensures QuickTime compatibility. It handles circular mask overlays for custom photo avatars and combines screen recordings with audio.

## External Dependencies

### AI & ML Services

-   **OpenAI**: Used for Turkish tutorial script generation (`OPENAI_API_KEY`).
-   **Anthropic**: Alternative AI script generation (`ANTHROPIC_API_KEY`).
-   **ElevenLabs**: Turkish text-to-speech conversion using `eleven_multilingual_v2` model (`ELEVENLABS_API_KEY`).
-   **D-ID**: AI talking avatar generation for lip-synced videos, integrates with Microsoft Azure TTS for Turkish (`DID_API_KEY`).

### Core Dependencies

-   **FastAPI**: Web framework for building the API.
-   **httpx**: Asynchronous HTTP client for external API calls.
-   **BeautifulSoup4**: For web scraping and HTML parsing from general URLs.
-   **Python Environment**: Managed by `uv` package manager.
-   **FFmpeg**: System dependency for video composition, concatenation, and audio muxing.
-   **Playwright**: Used by `ScreenRecorderService` for browser automation and screen recording.

### Content Source Integration

-   **GitHub API**: Analyzes public GitHub repositories (no API key needed for public repos).
-   **Web Scraping**: Uses BeautifulSoup4 for general website content extraction.
-   **Document Processing Libraries**: `PyPDF2`, `python-docx`, `markdown` for content extraction from PDF, DOCX, TXT, and MD files.