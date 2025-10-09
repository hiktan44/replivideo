"""
Website Analysis Service
Analyzes any website URL and extracts content for video generation
"""

import httpx
from typing import Dict
from bs4 import BeautifulSoup
import re


class WebsiteAnalyzer:
    """General website content analysis service"""
    
    @staticmethod
    async def analyze_website(url: str) -> Dict:
        """Extract content from any website URL"""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text().strip() if title else "Untitled Website"
                
                # Extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc.get('content', '') if meta_desc and hasattr(meta_desc, 'get') else ""
                description = description.strip() if description else ""
                
                # Extract main content
                main_content = ""
                
                # Try to find main content areas
                content_areas = (
                    soup.find('main') or 
                    soup.find('article') or 
                    soup.find('div', class_=re.compile(r'content|main|post|article', re.I)) or
                    soup.find('body')
                )
                
                if content_areas and hasattr(content_areas, 'find_all'):
                    # Get all paragraphs
                    paragraphs = content_areas.find_all(['p', 'h1', 'h2', 'h3', 'li'])
                    main_content = '\n'.join([p.get_text().strip() for p in paragraphs if hasattr(p, 'get_text') and p.get_text().strip()])
                
                # Extract headings for structure
                headings = []
                for i in range(1, 4):  # h1, h2, h3
                    for heading in soup.find_all(f'h{i}'):
                        headings.append({
                            'level': i,
                            'text': heading.get_text().strip()
                        })
                
                # Extract links for context
                links = []
                for link in soup.find_all('a', href=True)[:10]:  # First 10 links
                    link_text = link.get_text().strip()
                    if link_text:
                        links.append({
                            'text': link_text,
                            'url': link['href']
                        })
                
                # Clean and limit content
                main_content = main_content[:5000]  # Limit to 5000 chars
                
                return {
                    "type": "website",
                    "url": url,
                    "title": title_text,
                    "description": description or "No description available",
                    "content": main_content,
                    "headings": headings[:15],  # First 15 headings
                    "links": links,
                    "word_count": len(main_content.split()),
                    "language": "detected",  # Could add language detection
                    "success": True
                }
                
        except httpx.HTTPError as e:
            raise Exception(f"Website fetch error: {str(e)}")
        except Exception as e:
            raise Exception(f"Website analysis error: {str(e)}")
    
    @staticmethod
    def is_github_url(url: str) -> bool:
        """Check if URL is a GitHub repository"""
        url_lower = url.lower()
        return 'github.com' in url_lower and '/repos/' not in url_lower and '/api.' not in url_lower


class ContentAnalyzer:
    """Unified content analyzer that routes to appropriate service"""
    
    @staticmethod
    async def analyze_url(url: str) -> Dict:
        """Analyze any URL - GitHub repo or general website"""
        
        # Check if it's a GitHub repository URL
        if WebsiteAnalyzer.is_github_url(url):
            # Try GitHub analysis first
            try:
                # Check if it's a valid repo format
                parts = url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
                if len(parts) >= 2 and parts[0] and parts[1]:
                    # Import here to avoid circular imports
                    from main import GitHubAnalyzer
                    github_data = await GitHubAnalyzer.analyze_repo(url)
                    github_data["type"] = "github_repo"
                    return github_data
            except Exception as github_error:
                # If GitHub API fails, fall back to web scraping
                print(f"GitHub API failed, using web scraping: {github_error}")
        
        # Use general website analysis
        return await WebsiteAnalyzer.analyze_website(url)
