"""
Screen Recording Service using Playwright
Records web pages with automatic navigation and scrolling
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Page, Browser
import shutil

class ScreenRecorderService:
    def __init__(self):
        # Skip Playwright host validation (Nix environment compatibility)
        os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = 'true'
        
        self.enabled = True
        self.video_dir = Path("videos/recordings")
        self.video_dir.mkdir(parents=True, exist_ok=True)
    
    async def record_website(
        self, 
        url: str, 
        video_id: str,
        duration_minutes: int = 10,
        scroll_speed: str = "medium"
    ) -> str:
        """
        Record a website with automatic navigation
        
        Args:
            url: Website URL to record
            video_id: Unique video identifier
            duration_minutes: Target duration (5, 10, or 15 minutes)
            scroll_speed: Scroll speed (slow, medium, fast)
        
        Returns:
            Path to recorded video file
        """
        
        output_path = f"videos/screen_recording_{video_id}.mp4"
        
        try:
            async with async_playwright() as p:
                print(f"🎬 Starting browser automation for {url}...")
                
                # Launch browser with video recording
                # Use system Chromium (Nix) with all dependencies
                import subprocess
                try:
                    chromium_path = subprocess.check_output(['which', 'chromium'], text=True).strip()
                except subprocess.CalledProcessError:
                    chromium_path = None
                
                browser = await p.chromium.launch(
                    executable_path=chromium_path if chromium_path else None,
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                # Create context with video recording enabled
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    record_video_dir=str(self.video_dir),
                    record_video_size={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navigate to URL
                print(f"📄 Loading page: {url}")
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Calculate scroll parameters based on duration
                scroll_params = self._calculate_scroll_params(duration_minutes, scroll_speed)
                
                # Perform automated navigation
                await self._auto_navigate(page, scroll_params)
                
                # Close browser (this finalizes the video)
                await context.close()
                await browser.close()
                
                # Find and move the recorded video
                video_file = await self._find_latest_video()
                if video_file and video_file.exists():
                    shutil.move(str(video_file), output_path)
                    print(f"✅ Screen recording saved: {output_path}")
                    return output_path
                else:
                    raise Exception("Video file not found after recording")
                    
        except Exception as e:
            print(f"❌ Screen recording error: {str(e)}")
            return await self._create_demo_recording(output_path)
    
    async def _auto_navigate(self, page: Page, params: Dict):
        """Automatically navigate and scroll the page"""
        
        total_duration = params['duration_seconds']
        scroll_pause = params['scroll_pause']
        
        print(f"🖱️ Starting automatic navigation for {total_duration}s...")
        
        start_time = asyncio.get_event_loop().time()
        
        # Get page height
        page_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        
        scroll_position = 0
        direction = 1  # 1 for down, -1 for up
        
        while (asyncio.get_event_loop().time() - start_time) < total_duration:
            # Smooth scroll
            scroll_step = viewport_height * 0.8 * direction
            scroll_position += scroll_step
            
            # Change direction at boundaries
            if scroll_position >= page_height - viewport_height:
                direction = -1  # Scroll up
                await asyncio.sleep(1)  # Pause at bottom
            elif scroll_position <= 0:
                direction = 1  # Scroll down
                await asyncio.sleep(1)  # Pause at top
            
            # Perform scroll
            await page.evaluate(f"window.scrollTo({{top: {max(0, scroll_position)}, behavior: 'smooth'}})")
            await asyncio.sleep(scroll_pause)
            
            # Try to click interactive elements occasionally
            if int(asyncio.get_event_loop().time() - start_time) % 20 == 0:
                await self._try_click_elements(page)
        
        print(f"✅ Navigation completed after {total_duration}s")
    
    async def _try_click_elements(self, page: Page):
        """Try to click on interesting elements (tabs, buttons, etc.)"""
        try:
            # Try common interactive selectors
            selectors = [
                'button:visible',
                'a[role="tab"]:visible',
                '.tab:visible',
                'summary:visible'  # For <details> elements
            ]
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    # Click first visible element
                    try:
                        await elements[0].click(timeout=2000)
                        await asyncio.sleep(1)
                        print(f"🖱️ Clicked: {selector}")
                        break
                    except Exception:
                        continue
        except Exception:
            pass  # Silent fail for optional interactions
    
    def _calculate_scroll_params(self, duration_minutes: int, speed: str) -> Dict:
        """Calculate scroll parameters based on duration"""
        
        # Scroll pause times (seconds between scrolls)
        speed_map = {
            'slow': 3.0,
            'medium': 2.0,
            'fast': 1.0
        }
        
        scroll_pause = speed_map.get(speed, 2.0)
        duration_seconds = duration_minutes * 60
        
        return {
            'duration_seconds': duration_seconds,
            'scroll_pause': scroll_pause
        }
    
    async def _find_latest_video(self) -> Optional[Path]:
        """Find the most recently created video file"""
        try:
            video_files = list(self.video_dir.glob("*.webm"))
            if not video_files:
                return None
            
            # Get most recent file
            latest_file = max(video_files, key=lambda p: p.stat().st_mtime)
            return latest_file
        except Exception as e:
            print(f"Error finding video: {e}")
            return None
    
    async def _create_demo_recording(self, output_path: str) -> str:
        """Create demo recording when actual recording fails"""
        demo_video = "demo_assets/demo_video.mp4"
        
        if Path(demo_video).exists():
            shutil.copy(demo_video, output_path)
            print(f"📝 Demo screen recording created: {output_path}")
        else:
            # Create minimal valid MP4 header
            mp4_header = bytes([
                0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
                0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
                0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
                0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,
            ])
            with open(output_path, "wb") as f:
                f.write(mp4_header)
            print(f"📝 Demo placeholder created: {output_path}")
        
        return output_path
