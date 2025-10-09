# Quick Setup Guide

## 🚀 Getting Started in 3 Steps

### Step 1: API Keys (Optional for Demo)

The app works in **demo mode** without any API keys for testing. To use real AI features, add your keys:

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```env
# Choose one for AI script generation:
OPENAI_API_KEY=sk-...          # Get from platform.openai.com
# OR
ANTHROPIC_API_KEY=sk-ant-...   # Get from console.anthropic.com

# For Turkish voiceovers:
ELEVENLABS_API_KEY=...         # Get from elevenlabs.io

# For avatar videos:
DID_API_KEY=...                # Get from d-id.com
```

### Step 2: Run the Application

The server starts automatically. Just visit the app URL!

### Step 3: Create Your First Video

1. Enter a GitHub repository URL (e.g., `https://github.com/fastapi/fastapi`)
2. Choose your preferences:
   - **Avatar Type**: Professional or casual, male or female
   - **Voice Type**: Turkish professional or friendly voice
   - **Video Style**: Tutorial, review, or quick-start
3. Click "🚀 Video Oluştur" (Create Video)
4. Watch the progress in real-time
5. Download your video when complete!

## 📋 What Each API Does

| Service | Purpose | Required? |
|---------|---------|-----------|
| **OpenAI / Anthropic** | Generates 10-minute Turkish video script | No (uses demo script) |
| **ElevenLabs** | Creates Turkish voiceover | No (creates silent demo) |
| **D-ID** | Generates talking avatar videos | No (creates demo clips) |

## 💡 Demo Mode vs. Production

### Demo Mode (No API Keys)
- ✅ Full UI and workflow works
- ✅ GitHub analysis works
- ✅ Demo script generation
- ✅ Creates placeholder media files
- ✅ Complete video pipeline testing
- ❌ No real AI-generated content

### Production Mode (With API Keys)
- ✅ Real AI-generated Turkish scripts
- ✅ Professional Turkish voiceovers
- ✅ Realistic talking avatars
- ✅ 10-minute professional videos

## 🔍 Troubleshooting

### Video creation fails
- Check GitHub URL is valid and public
- View error message in the UI
- Check server logs for details

### API errors
- Verify API keys are correct
- Check API key has sufficient credits
- App will fall back to demo mode on API errors

### Download not working
- Ensure video status shows "completed"
- Video files are in `videos/` directory

## 📚 API Key Setup Links

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys
- **D-ID**: https://studio.d-id.com/account-settings

## 🎯 Next Steps

Once you have the basic app working:

1. **Add FFmpeg** for real video composition
2. **Implement screen recording** with Puppeteer
3. **Add YouTube upload** functionality
4. **Use PostgreSQL** for persistent storage
5. **Deploy to production** with publish feature
