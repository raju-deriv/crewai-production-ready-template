import structlog
from typing import List, Dict, Any, Optional, Union
import re

logger = structlog.get_logger(__name__)

class TextChunker:
    """
    Class for splitting text into smaller chunks for embedding.
    
    This class provides methods for splitting text into smaller chunks
    with configurable chunk size and overlap.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the TextChunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"Initialized TextChunker with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into smaller chunks.
        
        Args:
            text: Text to split into chunks.
        
        Returns:
            List[str]: List of text chunks.
        """
        if not text:
            return []
        
        # If text is shorter than chunk_size, return it as a single chunk
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Get a chunk of size chunk_size
            end = start + self.chunk_size
            
            # If we're at the end of the text, just add the remaining text
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a good splitting point (end of sentence or paragraph)
            # Look for period followed by space or newline, or just newline
            split_point = self._find_split_point(text, end)
            
            # Add the chunk
            chunks.append(text[start:split_point])
            
            # Move the start pointer, accounting for overlap
            start = split_point - self.chunk_overlap
            if start < 0:
                start = 0
        
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def _find_split_point(self, text: str, end: int) -> int:
        """
        Find a good splitting point near the end position.
        
        Args:
            text: Text to split.
            end: End position to look around.
        
        Returns:
            int: Position to split at.
        """
        # Look for a period followed by space or newline within 100 characters before end
        look_back = min(100, end)
        for i in range(end, end - look_back, -1):
            if i < len(text) and (
                (text[i-1] == '.' and (i == len(text) or text[i] in [' ', '\n'])) or
                text[i-1] == '\n'
            ):
                return i
        
        # If no good splitting point found, just split at end
        return end
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split documents into smaller chunks.
        
        Args:
            documents: List of documents to split into chunks.
                Each document should be a dictionary with at least:
                - 'text': Text content of the document
                - 'metadata': Dictionary of metadata about the document
        
        Returns:
            List[Dict[str, Any]]: List of document chunks.
        """
        chunked_documents = []
        
        for doc in documents:
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            
            # Skip empty documents
            if not text:
                continue
            
            # Split text into chunks
            chunks = self.chunk_text(text)
            
            # Create a new document for each chunk
            for i, chunk in enumerate(chunks):
                # Create a copy of the metadata
                chunk_metadata = metadata.copy()
                
                # Add chunk information to metadata
                chunk_metadata['chunk'] = {
                    'index': i,
                    'total': len(chunks)
                }
                
                # Create the chunked document
                chunked_doc = {
                    'text': chunk,
                    'metadata': chunk_metadata
                }
                
                # Copy other fields from the original document
                for key, value in doc.items():
                    if key not in ['text', 'metadata']:
                        chunked_doc[key] = value
                
                chunked_documents.append(chunked_doc)
        
        logger.debug(f"Split {len(documents)} documents into {len(chunked_documents)} chunks")
        return chunked_documents
