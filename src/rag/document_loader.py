"""Document loader for processing model documentation."""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    
    id: str
    content: str
    metadata: Dict[str, Any]
    source_file: str
    chunk_index: int
    start_char: int
    end_char: int


class DocumentLoader:
    """Loads and processes model documentation files."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        """Initialize the document loader.
        
        Args:
            chunk_size: Target size for document chunks in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
    def load_documents(self, docs_directory: str) -> List[DocumentChunk]:
        """Load all documents from a directory.
        
        Args:
            docs_directory: Path to directory containing documentation
            
        Returns:
            List of document chunks
        """
        docs_path = Path(docs_directory)
        if not docs_path.exists():
            logger.error("Documentation directory not found", path=docs_directory)
            return []
        
        chunks = []
        
        # Process all markdown files
        for file_path in docs_path.glob("*.md"):
            try:
                file_chunks = self._load_single_document(file_path)
                chunks.extend(file_chunks)
                logger.info(
                    "Loaded document",
                    file=file_path.name,
                    chunks_created=len(file_chunks)
                )
            except Exception as e:
                logger.error(
                    "Failed to load document",
                    file=file_path.name,
                    error=str(e)
                )
        
        logger.info("Document loading complete", total_chunks=len(chunks))
        return chunks
    
    def _load_single_document(self, file_path: Path) -> List[DocumentChunk]:
        """Load and chunk a single document.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of document chunks
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata from filename and content
        metadata = self._extract_metadata(file_path, content)
        
        # Split into chunks
        chunks = self._chunk_document(content, str(file_path), metadata)
        
        return chunks
    
    def _extract_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from document.
        
        Args:
            file_path: Path to the document
            content: Document content
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "filename": file_path.name,
            "model_id": file_path.stem,  # Use filename without extension as model ID
            "file_size": len(content),
            "doc_type": "model_documentation"
        }
        
        # Extract title from first heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        # Extract sections
        sections = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        if sections:
            metadata["sections"] = sections
        
        # Count capabilities mentions
        capabilities_matches = re.findall(
            r'\b(reasoning|creative|code|analysis|qa|conversation|summarization)\b',
            content.lower()
        )
        if capabilities_matches:
            metadata["mentioned_capabilities"] = list(set(capabilities_matches))
        
        # Extract cost information
        cost_matches = re.findall(r'\$(\d+\.?\d*)', content)
        if cost_matches:
            metadata["cost_mentions"] = [float(cost) for cost in cost_matches]
        
        # Extract performance metrics
        if re.search(r'\blatency\b', content.lower()):
            metadata["discusses_latency"] = True
        if re.search(r'\bquality\b', content.lower()):
            metadata["discusses_quality"] = True
        if re.search(r'\bavailability\b', content.lower()):
            metadata["discusses_availability"] = True
        
        return metadata
    
    def _chunk_document(
        self, 
        content: str, 
        source_file: str, 
        base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split document into chunks.
        
        Args:
            content: Document content
            source_file: Source file path
            base_metadata: Base metadata for all chunks
            
        Returns:
            List of document chunks
        """
        chunks = []
        
        # First try to split by sections (## headings)
        section_chunks = self._split_by_sections(content)
        
        if len(section_chunks) > 1:
            # Use section-based splitting
            char_offset = 0
            for i, section_content in enumerate(section_chunks):
                if len(section_content.strip()) >= self.min_chunk_size:
                    # Further split long sections if needed
                    sub_chunks = self._split_text_by_size(section_content)
                    
                    for j, sub_chunk in enumerate(sub_chunks):
                        chunk_id = f"{Path(source_file).stem}_section_{i}_chunk_{j}"
                        
                        # Extract section title
                        section_title = self._extract_section_title(section_content)
                        
                        chunk_metadata = {
                            **base_metadata,
                            "chunk_type": "section",
                            "section_index": i,
                            "sub_chunk_index": j,
                            "section_title": section_title
                        }
                        
                        chunk = DocumentChunk(
                            id=chunk_id,
                            content=sub_chunk.strip(),
                            metadata=chunk_metadata,
                            source_file=source_file,
                            chunk_index=len(chunks),
                            start_char=char_offset,
                            end_char=char_offset + len(sub_chunk)
                        )
                        chunks.append(chunk)
                        char_offset += len(sub_chunk)
        else:
            # Use size-based splitting for the entire document
            text_chunks = self._split_text_by_size(content)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk_id = f"{Path(source_file).stem}_chunk_{i}"
                
                chunk_metadata = {
                    **base_metadata,
                    "chunk_type": "text",
                    "chunk_index": i
                }
                
                start_char = i * (self.chunk_size - self.chunk_overlap)
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=chunk_text.strip(),
                    metadata=chunk_metadata,
                    source_file=source_file,
                    chunk_index=i,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text)
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_by_sections(self, content: str) -> List[str]:
        """Split content by markdown sections (## headings).
        
        Args:
            content: Document content
            
        Returns:
            List of section contents
        """
        # Split by ## headings
        sections = re.split(r'\n## ', content)
        
        if len(sections) > 1:
            # Add back the ## to non-first sections
            sections = [sections[0]] + [f"## {section}" for section in sections[1:]]
        
        return [section for section in sections if section.strip()]
    
    def _split_text_by_size(self, text: str) -> List[str]:
        """Split text into chunks by size.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break
            
            # Try to break at a sentence or paragraph boundary
            chunk_text = text[start:end]
            
            # Look for good break points (in order of preference)
            break_points = [
                chunk_text.rfind('\n\n'),  # Paragraph break
                chunk_text.rfind('\n'),    # Line break
                chunk_text.rfind('. '),    # Sentence end
                chunk_text.rfind(', '),    # Comma
                chunk_text.rfind(' ')      # Word boundary
            ]
            
            break_point = -1
            for bp in break_points:
                if bp > start + self.min_chunk_size:  # Ensure minimum chunk size
                    break_point = bp
                    break
            
            if break_point == -1:
                # No good break point found, just cut at size
                break_point = end
            
            chunk = text[start:break_point + 1].strip()
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
            
            # Calculate next start with overlap
            start = max(break_point + 1 - self.chunk_overlap, start + 1)
        
        return chunks
    
    def _extract_section_title(self, section_content: str) -> Optional[str]:
        """Extract title from section content.
        
        Args:
            section_content: Content of the section
            
        Returns:
            Section title if found
        """
        # Look for the first heading in the section
        title_match = re.search(r'^##\s+(.+)$', section_content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        # Look for # heading if no ## found
        title_match = re.search(r'^#\s+(.+)$', section_content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        return None
