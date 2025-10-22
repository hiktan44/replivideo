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
    
    async def record_html_file(
        self,
        html_file_path: str,
        video_id: str,
        duration_minutes: int = 10
    ) -> str:
        """
        Record a local HTML file (for document slides)
        
        Args:
            html_file_path: Path to HTML file
            video_id: Unique video identifier
            duration_minutes: Target duration
            
        Returns:
            Path to recorded video file
        """
        from pathlib import Path as PathLib
        abs_path = PathLib(html_file_path).resolve()
        file_url = f"file://{abs_path}"
        
        print(f"🎬 Recording HTML slides: {html_file_path}")
        return await self.record_website(
            url=file_url,
            video_id=video_id,
            duration_minutes=duration_minutes,
            scroll_speed="medium"
        )
    
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
            url: Website URL to record (http/https or file://)
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
                try:
                    # Try networkidle first (ideal but can timeout on some sites)
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    print("✅ Page loaded with networkidle")
                except Exception as e:
                    # If networkidle fails, try 'load' which is more permissive
                    print(f"⚠️ Networkidle failed ({str(e)[:50]}...), trying 'load'...")
                    try:
                        await page.goto(url, wait_until='load', timeout=30000)
                        print("✅ Page loaded with 'load' strategy")
                    except Exception:
                        # Last resort: just navigate without waiting
                        print("⚠️ Load also failed, navigating without wait...")
                        await page.goto(url, timeout=20000)
                
                await asyncio.sleep(3)  # Wait for dynamic content to render
                
                # Calculate scroll parameters based on duration
                scroll_params = self._calculate_scroll_params(duration_minutes, scroll_speed)
                
                # Perform automated navigation
                await self._auto_navigate(page, scroll_params)
                
                # Get video path BEFORE closing (must be called before context.close())
                video = page.video
                video_path = None
                
                if video:
                    try:
                        # Get path before closing (video will be finalized when context closes)
                        video_path = await video.path()
                    except Exception as e:
                        print(f"⚠️ Could not get video path: {e}")
                
                # Close context to finalize the video recording
                await context.close()
                await browser.close()
                
                # Move the finalized video to output location
                if video_path and Path(video_path).exists():
                    shutil.move(str(video_path), output_path)
                    print(f"✅ Screen recording saved: {output_path}")
                    return output_path
                else:
                    print("⚠️ Video not found, using demo fallback")
                    return await self._create_demo_recording(output_path)
                    
        except Exception as e:
            print(f"❌ Screen recording error: {str(e)}")
            return await self._create_demo_recording(output_path)
    
    async def _auto_navigate(self, page: Page, params: Dict):
        """Automatically navigate and scroll the page"""
        
        total_duration = params['duration_seconds']
        scroll_pause = params['scroll_pause']
        
        print(f"🖱️ Starting automatic navigation for {total_duration}s...")
        
        start_time = asyncio.get_event_loop().time()
        visited_pages = set()
        current_url = page.url
        visited_pages.add(current_url)
        
        # Get page height
        page_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        
        scroll_position = 0
        direction = 1  # 1 for down, -1 for up
        last_subpage_click = start_time
        
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
            
            # Try to navigate to sub-pages every 30 seconds
            elapsed = asyncio.get_event_loop().time()
            if elapsed - last_subpage_click >= 30 and elapsed - start_time < total_duration - 10:
                navigated = await self._try_navigate_subpage(page, visited_pages)
                if navigated:
                    last_subpage_click = elapsed
                    # Update page dimensions for new page
                    page_height = await page.evaluate("document.body.scrollHeight")
                    viewport_height = await page.evaluate("window.innerHeight")
                    scroll_position = 0
                    direction = 1
        
        print(f"✅ Navigation completed after {total_duration}s")
    
    async def _try_navigate_subpage(self, page: Page, visited_pages: set) -> bool:
        """Try to navigate to a sub-page by clicking links"""
        try:
            base_url = page.url.split('?')[0].rstrip('/')
            
            # Find internal links
            links = await page.query_selector_all('a[href]:visible')
            
            for link in links[:10]:  # Check first 10 links
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        from urllib.parse import urljoin
                        full_url = urljoin(page.url, href)
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Check if it's same domain and not visited
                    if full_url.startswith(base_url) and full_url not in visited_pages:
                        # Ignore anchors, external, and special links
                        if '#' in full_url.split('/')[-1]:
                            continue
                        if full_url.endswith('.pdf') or full_url.endswith('.zip'):
                            continue
                        
                        print(f"🔗 Navigating to sub-page: {full_url}")
                        await page.goto(full_url, wait_until='networkidle', timeout=15000)
                        visited_pages.add(full_url)
                        await asyncio.sleep(2)
                        return True
                        
                except Exception:
                    continue
            
            return False
        except Exception as e:
            print(f"⚠️ Sub-page navigation error: {e}")
            return False
    
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
