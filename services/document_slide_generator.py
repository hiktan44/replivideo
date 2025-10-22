"""
Document Slide Generator Service
Converts document content into beautiful HTML slides for screen recording
"""
import re
from typing import List, Dict
from pathlib import Path


class DocumentSlideGenerator:
    """Generate HTML slides from document content"""
    
    @staticmethod
    def split_into_sections(content: str, max_words_per_slide: int = 120) -> List[Dict[str, str]]:
        """
        Split document content into logical sections for slides
        
        Args:
            content: Document text content
            max_words_per_slide: Maximum words per slide
            
        Returns:
            List of sections with title and content
        """
        sections = []
        lines = content.split('\n')
        current_section = {"title": "", "content": []}
        word_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect titles (short lines, capitalized, or with special markers)
            is_title = (
                len(line) < 60 and 
                (line.isupper() or 
                 line[0].isupper() and ':' not in line or
                 re.match(r'^[\d\.\)]+\s', line))  # Numbered titles
            )
            
            if is_title and word_count > 30:  # Start new section if we have enough content
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": line, "content": []}
                word_count = 0
            elif is_title and not current_section["title"]:
                current_section["title"] = line
            else:
                current_section["content"].append(line)
                word_count += len(line.split())
                
                # Split if too long
                if word_count > max_words_per_slide:
                    sections.append(current_section)
                    current_section = {"title": "", "content": []}
                    word_count = 0
        
        # Add last section
        if current_section["content"]:
            sections.append(current_section)
        
        # If no sections found, create default sections
        if not sections:
            words = content.split()
            for i in range(0, len(words), max_words_per_slide):
                chunk = ' '.join(words[i:i + max_words_per_slide])
                sections.append({
                    "title": f"Bölüm {len(sections) + 1}",
                    "content": [chunk]
                })
        
        return sections
    
    @staticmethod
    def generate_slide_html(section: Dict[str, str], slide_number: int, total_slides: int) -> str:
        """
        Generate beautiful HTML for a single slide
        
        Args:
            section: Section with title and content
            slide_number: Current slide number
            total_slides: Total number of slides
            
        Returns:
            HTML string for the slide
        """
        title = section.get("title", f"Bölüm {slide_number}")
        content_lines = section.get("content", [])
        content_html = "<br><br>".join(content_lines)
        
        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
        }}
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 min-h-screen flex items-center justify-center p-12">
    <div class="max-w-5xl w-full">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-5xl font-bold text-gray-800 mb-4 leading-tight">
                {title}
            </h1>
            <div class="h-2 w-32 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"></div>
        </div>
        
        <!-- Content -->
        <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-10 border border-gray-200">
            <div class="text-2xl text-gray-700 leading-relaxed space-y-4">
                {content_html}
            </div>
        </div>
        
        <!-- Footer -->
        <div class="mt-8 flex justify-between items-center text-gray-500">
            <div class="text-lg">📄 Doküman İçeriği</div>
            <div class="text-lg font-semibold">{slide_number} / {total_slides}</div>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    @staticmethod
    async def create_slides_from_document(content: str, video_id: str) -> str:
        """
        Create HTML slides from document content and save to temp file
        
        Args:
            content: Document text content
            video_id: Video ID for unique filename
            
        Returns:
            Path to the HTML file with all slides
        """
        # Split content into sections
        sections = DocumentSlideGenerator.split_into_sections(content)
        total_slides = len(sections)
        
        print(f"📊 Created {total_slides} slides from document")
        
        # Generate combined HTML with all slides
        slides_html = []
        for i, section in enumerate(sections, 1):
            slide_html = DocumentSlideGenerator.generate_slide_html(section, i, total_slides)
            slides_html.append(slide_html)
        
        # Create container HTML that can navigate between slides
        combined_html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Slides</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
        }}
        .slide {{
            display: none;
        }}
        .slide.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div id="slides-container">
"""
        
        for i, slide_html in enumerate(slides_html, 1):
            # Extract body content
            body_match = re.search(r'<body[^>]*>(.*?)</body>', slide_html, re.DOTALL)
            if body_match:
                body_content = body_match.group(1)
                active_class = "active" if i == 1 else ""
                combined_html += f'<div class="slide {active_class}" id="slide-{i}">{body_content}</div>\n'
        
        combined_html += """
    </div>
    
    <script>
        let currentSlide = 1;
        const totalSlides = """ + str(total_slides) + """;
        const slideInterval = 8000; // 8 seconds per slide
        
        function showSlide(n) {
            const slides = document.getElementsByClassName('slide');
            for (let i = 0; i < slides.length; i++) {
                slides[i].classList.remove('active');
            }
            if (n > slides.length) { n = slides.length; }
            if (n < 1) { n = 1; }
            slides[n - 1].classList.add('active');
            currentSlide = n;
        }
        
        function nextSlide() {
            if (currentSlide < totalSlides) {
                showSlide(currentSlide + 1);
            }
        }
        
        // Auto-advance slides
        setInterval(nextSlide, slideInterval);
        
        // Expose function for external control
        window.showSlide = showSlide;
        window.nextSlide = nextSlide;
    </script>
</body>
</html>
"""
        
        # Save to temp file
        slides_dir = Path("videos/temp/slides")
        slides_dir.mkdir(parents=True, exist_ok=True)
        
        slides_file = slides_dir / f"slides_{video_id}.html"
        slides_file.write_text(combined_html, encoding='utf-8')
        
        print(f"✅ Slides HTML saved: {slides_file}")
        return str(slides_file)
