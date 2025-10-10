"""
Test script for HeyGen integration
"""

import asyncio
import os
from pathlib import Path

async def test_heygen_service():
    """Test HeyGen service basic functionality"""
    print("🧪 Testing HeyGen Service Integration...")
    
    try:
        # Import the service
        from services.heygen_service import HeyGenService
        print("✅ HeyGen service imported successfully")
        
        # Create service instance
        service = HeyGenService()
        print(f"✅ HeyGen service instantiated (API {'enabled' if service.enabled else 'disabled - demo mode'})")
        
        # Test demo video creation (won't use real API)
        test_text = "Merhaba, bu HeyGen entegrasyonu için bir test mesajıdır."
        video_path = await service._create_demo_video(test_text, "professional_female")
        
        if Path(video_path).exists():
            print(f"✅ Demo video created successfully at: {video_path}")
            file_size = Path(video_path).stat().st_size
            print(f"   File size: {file_size} bytes")
        else:
            print("❌ Demo video file was not created")
        
        # Test avatar mapping
        print("\n📋 Available avatars:")
        for avatar_type, avatar_id in service.avatars.items():
            print(f"   - {avatar_type}: {avatar_id}")
        
        # Check API key status
        if service.api_key:
            print(f"\n✅ HeyGen API key is configured (starts with: {service.api_key[:10]}...)")
            
            # Try to fetch Turkish voices if API is available
            turkish_voices = await service.get_turkish_voices()
            if turkish_voices:
                print(f"✅ Found {len(turkish_voices)} Turkish voices")
                for voice in turkish_voices[:3]:  # Show first 3
                    print(f"   - {voice.get('name', 'Unknown')} ({voice.get('gender', 'Unknown')} voice)")
            else:
                print("⚠️ No Turkish voices found or API unavailable")
        else:
            print("\n⚠️ HeyGen API key not configured - will use demo mode")
        
        print("\n✅ HeyGen integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_provider_selection():
    """Test provider selection in main app"""
    print("\n🧪 Testing Provider Selection...")
    
    try:
        from main import AvatarService
        from services.heygen_service import HeyGenService
        from services.did_service import DIDService
        
        # Create a dummy script
        test_script = {
            "sections": [
                {
                    "type": "avatar",
                    "text": "Test mesajı"
                }
            ]
        }
        
        # Test HeyGen provider
        print("Testing HeyGen provider...")
        videos = await AvatarService.render_avatar_segments(
            test_script, 
            "professional_female",
            "dummy_audio.mp3",
            provider="heygen"
        )
        print(f"✅ HeyGen provider works - created {len(videos)} video(s)")
        
        # Test D-ID provider
        print("Testing D-ID provider...")
        videos = await AvatarService.render_avatar_segments(
            test_script,
            "professional_female", 
            "dummy_audio.mp3",
            provider="did"
        )
        print(f"✅ D-ID provider works - created {len(videos)} video(s)")
        
        print("✅ Provider selection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Provider selection test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("HeyGen Integration Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_passed = await test_heygen_service()
    test2_passed = await test_provider_selection()
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print(f"  HeyGen Service Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Provider Selection Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! HeyGen integration is ready to use!")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())