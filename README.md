# 🎬 AI Avatar Video Maker

Automatically generate 10-minute Turkish tutorial videos from GitHub repositories using AI avatars and professional voiceovers.

## ✨ Features

- **GitHub Analysis**: Automatically extracts repository information, README, languages, and statistics
- **AI Script Generation**: Creates professional 10-minute Turkish video scripts using OpenAI or Anthropic
- **Turkish Text-to-Speech**: High-quality Turkish voiceovers with ElevenLabs
- **Avatar Videos**: Professional talking avatars for intros and transitions using D-ID
- **Real-time Progress Tracking**: Monitor video creation stages in real-time
- **Web Interface**: Simple and intuitive UI for video creation

## 🚀 Quick Start

### 1. Install Dependencies

Dependencies are already installed via `uv`. If you need to reinstall:

```bash
uv sync
```

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```env
# Choose one for script generation
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key

# For Turkish text-to-speech
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# For avatar videos
DID_API_KEY=your_did_api_key
```

### 3. Run the Application

```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

The application will be available at `http://localhost:5000`

## 📝 How to Use

1. Open the web interface
2. Enter a GitHub repository URL (e.g., `https://github.com/owner/repo`)
3. Choose avatar type, voice type, and video style
4. Click "Video Oluştur" (Create Video)
5. Monitor the progress in real-time
6. Download the completed video

## 🔑 API Keys Setup

### OpenAI API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys section
3. Create a new API key
4. Add to `.env` as `OPENAI_API_KEY`

### Anthropic API Key (Alternative to OpenAI)
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Generate an API key
3. Add to `.env` as `ANTHROPIC_API_KEY`

### ElevenLabs API Key
1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Go to Profile + API Key
3. Copy your API key
4. Add to `.env` as `ELEVENLABS_API_KEY`

### D-ID API Key
1. Sign up at [d-id.com](https://www.d-id.com)
2. Go to Account Settings
3. Generate API key
4. Add to `.env` as `DID_API_KEY`

## 🎨 Video Structure

The generated videos follow this 10-minute structure:

- **[00:00-00:30]** Opening with avatar introduction
- **[00:30-02:00]** Project overview and description
- **[02:00-02:20]** Transition 1 (avatar)
- **[02:20-05:00]** Main features deep dive
- **[05:00-05:20]** Transition 2 (avatar)
- **[05:20-08:00]** Demo and usage examples
- **[08:00-08:20]** Transition 3 (avatar)
- **[08:20-09:30]** Installation guide
- **[09:30-10:00]** Closing summary (avatar)

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **AI Script Generation**: OpenAI GPT-4 or Anthropic Claude
- **Text-to-Speech**: ElevenLabs (Turkish voices)
- **Avatar Videos**: D-ID API
- **GitHub Data**: GitHub REST API
- **Frontend**: HTML + Tailwind CSS

## 📚 Project Structure

```
.
├── main.py                 # FastAPI application
├── services/
│   ├── ai_service.py      # AI script generation
│   ├── elevenlabs_service.py  # Text-to-speech
│   └── did_service.py     # Avatar video generation
├── videos/                # Generated videos (gitignored)
├── .env                   # API keys (gitignored)
└── README.md
```

## 🎯 Customization Options

### Avatar Types
- `professional_female`: Professional female presenter
- `professional_male`: Professional male presenter
- `casual_female`: Casual female presenter
- `casual_male`: Casual male presenter

### Voice Types
- `tr_female_professional`: Turkish professional female voice
- `tr_male_professional`: Turkish professional male voice
- `tr_female_friendly`: Turkish friendly female voice

### Video Styles
- `tutorial`: Educational tutorial style
- `review`: Review and analysis style
- `quick_start`: Quick start guide style

## 🚧 Demo Mode

The application works in demo mode even without API keys:
- Uses placeholder scripts when AI APIs are not configured
- Creates demo audio files instead of real speech
- Creates demo avatar placeholders instead of real videos

This allows you to test the workflow before setting up paid API services.

## 📄 License

This project is for educational and demonstration purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## HeyGen v3 (2026-10-31)

The HeyGen adapter uses `POST /v3/videos`, `GET /v3/videos/{video_id}` and paginated `GET /v3/voices?language=Turkish`. It explicitly selects `engine: {type: "avatar_iii"}` to retain the former Studio renderer, with 720p landscape output and the existing white background. v3 does not use the legacy `code: 100`, `video_inputs`, `dimension` or `test` fields.

The API key stays on the backend as `HEYGEN_API_KEY`. Missing configuration, voices or provider failures retain the existing local demo fallback; that fallback never submits a second paid request. Public avatar IDs are still the configured presets; their availability and account entitlements must be checked with the workspace before a paid end-to-end run.

Run the offline contract suite with:

```bash
python -m unittest discover -s tests -p test_heygen_integration.py -v
```

All HTTP requests and sleeps in that suite are mocked, even if a real key exists in the environment. It replaces the previous test script that could submit paid generations and print a key prefix. No paid API call or production deployment was performed for this migration.

Reference: [HeyGen migration guide](https://developers.heygen.com/endpoint-version-comparison), [create video](https://developers.heygen.com/reference/create-video), [list voices](https://developers.heygen.com/reference/list-voices).
