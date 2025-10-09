# HeyGen Integration Setup Guide

## ✅ Integration Complete!

The HeyGen API service has been successfully integrated into the AI Avatar Video Maker application.

## Features Added

1. **HeyGen Service Module** (`services/heygen_service.py`)
   - Full HeyGen API v2 integration
   - Turkish voice support with automatic detection
   - Video generation with status polling
   - Automatic video download and local storage
   - Demo mode fallback when API key is not available

2. **Provider Selection**
   - New "Avatar Sağlayıcı" (Avatar Provider) dropdown in UI
   - Support for both HeyGen and D-ID providers
   - HeyGen is set as the default (recommended) provider

3. **Advantages of HeyGen over D-ID**
   - **3x more text capacity**: 1,500 characters vs 500 characters
   - Better Turkish voice quality and selection
   - More modern avatar options
   - Improved video generation speed

## Setting Up the API Key

To enable HeyGen API functionality:

1. **Get your HeyGen API Key**
   - Sign up at https://heygen.com
   - Navigate to Settings > API
   - Copy your API key

2. **Set the Environment Variable**
   ```bash
   export HEYGEN_API_KEY="your-api-key-here"
   ```

   Or in Replit:
   - Go to the Secrets tab (🔒 icon in the sidebar)
   - Add a new secret:
     - Key: `HEYGEN_API_KEY`
     - Value: Your HeyGen API key

## Available Avatars

The integration includes 4 pre-configured avatars:
- **Professional Female**: Daisy-inskirt-20220818
- **Professional Male**: Josh_lite3_20230714
- **Casual Female**: Anna_public_3_20240108
- **Casual Male**: Lucas_public_2_20240210

## Usage

1. Open the application at http://localhost:5000
2. Select "HeyGen (Önerilen)" from the Avatar Provider dropdown
3. Enter any website or GitHub repository URL
4. Choose your avatar, voice, and video style preferences
5. Click "🚀 Video Oluştur" to generate your video

## Demo Mode

When the HeyGen API key is not configured:
- The application automatically falls back to demo mode
- A placeholder video file is created
- No actual API calls are made
- Perfect for testing the integration without consuming API credits

## Testing

Run the test suite to verify the integration:
```bash
python test_heygen_integration.py
```

## API Endpoints Used

- **List Voices**: `GET https://api.heygen.com/v2/voices`
- **Generate Video**: `POST https://api.heygen.com/v2/video/generate`
- **Check Status**: `GET https://api.heygen.com/v2/video/status`

## Troubleshooting

1. **API Key Not Working**
   - Verify the key is correctly set in environment variables
   - Check your HeyGen account for API access and credits

2. **Turkish Voices Not Found**
   - The service automatically fetches available Turkish voices
   - Falls back to demo mode if no Turkish voices are available

3. **Video Generation Timeout**
   - The service waits up to 2 minutes for video generation
   - Check your HeyGen dashboard for any issues

## Support

For HeyGen API documentation: https://docs.heygen.com/
For application issues: Check the console logs or run the test suite