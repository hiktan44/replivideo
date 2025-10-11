"""
Document Analysis Service
Extracts content from PDF, DOCX, TXT, and Markdown files for video generation
"""

from typing import Dict
from PyPDF2 import PdfReader
from docx import Document
import markdown
from pathlib import Path


class DocumentAnalyzer:
    """Document content extraction service"""
    
    SUPPORTED_FORMATS = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'markdown': 'text/markdown'
    }
    
    MAX_CONTENT_LENGTH = 10000  # Maximum characters to extract
    
    @staticmethod
    async def analyze_document(file_path: str, filename: str) -> Dict:
        """Extract content from uploaded document"""
        try:
            # Detect file type from extension
            file_ext = Path(filename).suffix.lower().lstrip('.')
            
            if file_ext not in DocumentAnalyzer.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            # Extract content based on file type
            if file_ext == 'pdf':
                content_data = DocumentAnalyzer._extract_from_pdf(file_path)
            elif file_ext == 'docx':
                content_data = DocumentAnalyzer._extract_from_docx(file_path)
            elif file_ext == 'txt':
                content_data = DocumentAnalyzer._extract_from_txt(file_path)
            elif file_ext in ['md', 'markdown']:
                content_data = DocumentAnalyzer._extract_from_markdown(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            return {
                "type": "document",
                "file_type": file_ext,
                "filename": filename,
                "title": content_data.get("title", filename),
                "content": content_data.get("content", ""),
                "word_count": len(content_data.get("content", "").split()),
                "headings": content_data.get("headings", []),
                "truncated": content_data.get("truncated", False),
                "original_length": content_data.get("original_length"),
                "success": True
            }
            
        except Exception as e:
            raise Exception(f"Document analysis error: {str(e)}")
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> Dict:
        """Extract text from PDF file"""
        try:
            reader = PdfReader(file_path)
            
            # Extract text from all pages (handle None returns)
            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:  # Only add if not None
                    full_text += page_text + "\n"
            
            # Clean up text
            full_text = full_text.strip()
            
            # Limit content length with warning
            was_truncated = False
            original_length = len(full_text)
            if original_length > DocumentAnalyzer.MAX_CONTENT_LENGTH:
                full_text = full_text[:DocumentAnalyzer.MAX_CONTENT_LENGTH] + "..."
                was_truncated = True
                print(f"⚠️ Content truncated: {original_length} → {DocumentAnalyzer.MAX_CONTENT_LENGTH} chars")
            
            # Try to extract title from first line or metadata
            title = "PDF Document"
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title
            elif full_text:
                first_line = full_text.split('\n')[0].strip()
                if len(first_line) < 100:
                    title = first_line
            
            # Extract headings (lines that look like headings)
            headings = []
            lines = full_text.split('\n')
            for i, line in enumerate(lines[:50]):  # Check first 50 lines
                line = line.strip()
                if line and len(line) < 100 and line[0].isupper() and not line.endswith('.'):
                    headings.append({
                        'level': 1 if i < 5 else 2,
                        'text': line
                    })
            
            return {
                "title": title,
                "content": full_text,
                "headings": headings[:10],
                "truncated": was_truncated,
                "original_length": original_length if was_truncated else None
            }
            
        except Exception as e:
            raise Exception(f"PDF extraction error: {str(e)}")
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> Dict:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            
            # Extract title from document properties
            title = "Word Document"
            if doc.core_properties.title:
                title = doc.core_properties.title
            
            # Extract headings and content
            headings = []
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Check if it's a heading
                if para.style and para.style.name and para.style.name.startswith('Heading'):
                    level = int(para.style.name.replace('Heading ', '')) if para.style.name[-1].isdigit() else 1
                    headings.append({
                        'level': level,
                        'text': text
                    })
                    # Use first heading as title if no title set
                    if title == "Word Document" and level == 1:
                        title = text
                
                paragraphs.append(text)
            
            # Combine content
            full_text = '\n'.join(paragraphs)
            
            # Limit content length with warning
            was_truncated = False
            original_length = len(full_text)
            if original_length > DocumentAnalyzer.MAX_CONTENT_LENGTH:
                full_text = full_text[:DocumentAnalyzer.MAX_CONTENT_LENGTH] + "..."
                was_truncated = True
                print(f"⚠️ Content truncated: {original_length} → {DocumentAnalyzer.MAX_CONTENT_LENGTH} chars")
            
            return {
                "title": title,
                "content": full_text,
                "headings": headings[:15],
                "truncated": was_truncated,
                "original_length": original_length if was_truncated else None
            }
            
        except Exception as e:
            raise Exception(f"DOCX extraction error: {str(e)}")
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> Dict:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()
            
            # Clean up text
            full_text = full_text.strip()
            
            # Limit content length with warning
            was_truncated = False
            original_length = len(full_text)
            if original_length > DocumentAnalyzer.MAX_CONTENT_LENGTH:
                full_text = full_text[:DocumentAnalyzer.MAX_CONTENT_LENGTH] + "..."
                was_truncated = True
                print(f"⚠️ Content truncated: {original_length} → {DocumentAnalyzer.MAX_CONTENT_LENGTH} chars")
            
            # Extract title from first line
            title = "Text Document"
            if full_text:
                first_line = full_text.split('\n')[0].strip()
                if len(first_line) < 100:
                    title = first_line
            
            # Extract potential headings (lines that are short and capitalized)
            headings = []
            lines = full_text.split('\n')
            for i, line in enumerate(lines[:50]):
                line = line.strip()
                if line and len(line) < 100 and line[0].isupper() and not line.endswith('.'):
                    headings.append({
                        'level': 1 if i < 5 else 2,
                        'text': line
                    })
            
            return {
                "title": title,
                "content": full_text,
                "headings": headings[:10],
                "truncated": was_truncated,
                "original_length": original_length if was_truncated else None
            }
            
        except Exception as e:
            raise Exception(f"TXT extraction error: {str(e)}")
    
    @staticmethod
    def _extract_from_markdown(file_path: str) -> Dict:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                md_text = f.read()
            
            # Convert markdown to HTML for better parsing
            html = markdown.markdown(md_text)
            
            # Also keep plain text version
            full_text = md_text.strip()
            
            # Limit content length with warning
            was_truncated = False
            original_length = len(full_text)
            if original_length > DocumentAnalyzer.MAX_CONTENT_LENGTH:
                full_text = full_text[:DocumentAnalyzer.MAX_CONTENT_LENGTH] + "..."
                was_truncated = True
                print(f"⚠️ Content truncated: {original_length} → {DocumentAnalyzer.MAX_CONTENT_LENGTH} chars")
            
            # Extract title from first heading
            title = "Markdown Document"
            lines = md_text.split('\n')
            for line in lines[:10]:
                if line.startswith('#'):
                    title = line.lstrip('#').strip()
                    break
            
            # Extract headings from markdown
            headings = []
            for line in lines:
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    text = line.lstrip('#').strip()
                    if text:
                        headings.append({
                            'level': min(level, 6),
                            'text': text
                        })
            
            return {
                "title": title,
                "content": full_text,
                "headings": headings[:15],
                "truncated": was_truncated,
                "original_length": original_length if was_truncated else None
            }
            
        except Exception as e:
            raise Exception(f"Markdown extraction error: {str(e)}")
    
    @staticmethod
    def is_supported_document(filename: str) -> bool:
        """Check if file format is supported"""
        file_ext = Path(filename).suffix.lower().lstrip('.')
        return file_ext in DocumentAnalyzer.SUPPORTED_FORMATS
    
    @staticmethod
    def get_content_type(filename: str) -> str:
        """Get MIME content type for file"""
        file_ext = Path(filename).suffix.lower().lstrip('.')
        return DocumentAnalyzer.SUPPORTED_FORMATS.get(file_ext, 'application/octet-stream')
