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
    def split_into_sections(content: str, max_words_per_slide: int = 80) -> List[Dict[str, str]]:
        """
        Split document content into logical sections for slides
        
        Args:
            content: Document text content
            max_words_per_slide: Maximum words per slide (reduced for better readability)
            
        Returns:
            List of sections with title and content (sentences)
        """
        sections = []
        lines = content.split('\n')
        current_section = {"title": "", "sentences": []}
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
                 re.match(r'^[\d\.\)]+\s', line))
            )
            
            if is_title and word_count > 20:
                if current_section["sentences"]:
                    sections.append(current_section)
                current_section = {"title": line, "sentences": []}
                word_count = 0
            elif is_title and not current_section["title"]:
                current_section["title"] = line
            else:
                # Split line into sentences for better highlighting
                sentences = re.split(r'([.!?]+\s+)', line)
                for i in range(0, len(sentences) - 1, 2):
                    sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
                    sentence = sentence.strip()
                    if sentence:
                        current_section["sentences"].append(sentence)
                        word_count += len(sentence.split())
                
                # If remaining text without punctuation
                if len(sentences) % 2 == 1 and sentences[-1].strip():
                    current_section["sentences"].append(sentences[-1].strip())
                    word_count += len(sentences[-1].split())
                
                # Split if too long
                if word_count > max_words_per_slide:
                    sections.append(current_section)
                    current_section = {"title": "", "sentences": []}
                    word_count = 0
        
        # Add last section
        if current_section["sentences"]:
            sections.append(current_section)
        
        # If no sections found, create default sections
        if not sections:
            words = content.split()
            for i in range(0, len(words), max_words_per_slide):
                chunk = ' '.join(words[i:i + max_words_per_slide])
                sections.append({
                    "title": f"Bölüm {len(sections) + 1}",
                    "sentences": [chunk]
                })
        
        return sections
    
    @staticmethod
    def generate_slide_html(section: Dict[str, str], slide_number: int, total_slides: int) -> str:
        """
        Generate FULL-SCREEN HTML slide with sentence-by-sentence highlighting
        
        Args:
            section: Section with title and sentences
            slide_number: Current slide number
            total_slides: Total number of slides
            
        Returns:
            HTML string for the slide
        """
        title = section.get("title", f"Bölüm {slide_number}")
        sentences = section.get("sentences", [])
        
        # Create sentence spans for progressive highlighting
        sentence_spans = []
        for i, sentence in enumerate(sentences):
            sentence_spans.append(
                f'<span class="sentence" data-index="{i}">{sentence}</span>'
            )
        
        content_html = ' '.join(sentence_spans)
        
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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .sentence {{
            transition: all 0.5s ease;
            padding: 8px 12px;
            border-radius: 6px;
            display: inline-block;
            margin: 4px 0;
        }}
        
        .sentence.active {{
            background: linear-gradient(120deg, #ffd93d 0%, #ffb800 100%);
            color: #000;
            font-weight: 600;
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(255, 185, 0, 0.4);
        }}
        
        .sentence.past {{
            opacity: 0.5;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1.05); }}
            50% {{ transform: scale(1.08); }}
        }}
        
        .sentence.active {{
            animation: pulse 2s ease-in-out infinite;
        }}
    </style>
</head>
<body class="bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 min-h-screen flex items-center justify-center p-8">
    <div class="w-full h-full flex flex-col justify-center">
        <!-- Title - EXTRA LARGE -->
        <div class="mb-10 text-center">
            <h1 class="text-7xl font-black text-white mb-6 leading-tight drop-shadow-2xl">
                {title}
            </h1>
            <div class="h-3 w-48 mx-auto bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full shadow-lg"></div>
        </div>
        
        <!-- Content - FULL SCREEN, HUGE TEXT -->
        <div class="bg-white/95 backdrop-blur-lg rounded-3xl shadow-2xl p-16 border-4 border-white/50 mx-auto max-w-7xl">
            <div id="content" class="text-5xl text-gray-800 leading-loose tracking-wide">
                {content_html}
            </div>
        </div>
        
        <!-- Footer - Minimal -->
        <div class="mt-8 flex justify-between items-center text-white/70 px-8">
            <div class="text-2xl">📄 Doküman</div>
            <div class="text-2xl font-bold">{slide_number} / {total_slides}</div>
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
        const slideInterval = 10000; // 10 seconds per slide (more time for reading)
        
        let currentSentenceIndex = 0;
        let sentenceHighlightInterval = null;
        
        function showSlide(n) {
            const slides = document.getElementsByClassName('slide');
            for (let i = 0; i < slides.length; i++) {
                slides[i].classList.remove('active');
            }
            if (n > slides.length) { n = slides.length; }
            if (n < 1) { n = 1; }
            slides[n - 1].classList.add('active');
            currentSlide = n;
            
            // Reset sentence highlighting for new slide
            startSentenceHighlighting();
        }
        
        function startSentenceHighlighting() {
            // Clear existing interval
            if (sentenceHighlightInterval) {
                clearInterval(sentenceHighlightInterval);
            }
            
            // Get all sentences in current slide
            const currentSlideElement = document.querySelector('.slide.active');
            if (!currentSlideElement) return;
            
            const sentences = currentSlideElement.querySelectorAll('.sentence');
            if (sentences.length === 0) return;
            
            // Reset all sentences
            sentences.forEach(s => {
                s.classList.remove('active', 'past');
            });
            
            currentSentenceIndex = 0;
            
            // Calculate time per sentence (evenly distribute slide time)
            const timePerSentence = slideInterval / sentences.length;
            
            // Highlight first sentence immediately
            if (sentences[0]) {
                sentences[0].classList.add('active');
            }
            
            // Progressive highlighting
            sentenceHighlightInterval = setInterval(() => {
                if (currentSentenceIndex < sentences.length) {
                    // Mark previous as past
                    if (currentSentenceIndex > 0) {
                        sentences[currentSentenceIndex - 1].classList.remove('active');
                        sentences[currentSentenceIndex - 1].classList.add('past');
                    }
                    
                    // Highlight current
                    if (sentences[currentSentenceIndex]) {
                        sentences[currentSentenceIndex].classList.add('active');
                        
                        // Smooth scroll to active sentence
                        sentences[currentSentenceIndex].scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }
                    
                    currentSentenceIndex++;
                }
            }, timePerSentence);
        }
        
        function nextSlide() {
            if (currentSlide < totalSlides) {
                showSlide(currentSlide + 1);
            }
        }
        
        // Auto-advance slides
        setInterval(nextSlide, slideInterval);
        
        // Start sentence highlighting on first slide
        startSentenceHighlighting();
        
        // Expose functions for external control
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
