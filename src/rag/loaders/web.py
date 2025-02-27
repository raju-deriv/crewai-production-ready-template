import structlog
import requests
from bs4 import BeautifulSoup
import time
import hashlib
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse
from src.rag.loaders.base import DocumentLoader

logger = structlog.get_logger(__name__)

class WebLoader(DocumentLoader):
    """
    Loader for web pages.
    
    This class implements the DocumentLoader interface for web pages.
    It provides methods for loading documents from URLs.
    """
    
    def __init__(self, timeout: int = 10, user_agent: Optional[str] = None):
        """
        Initialize the WebLoader.
        
        Args:
            timeout: Timeout for HTTP requests in seconds.
            user_agent: User agent string to use for HTTP requests.
        """
        self.timeout = timeout
        self.user_agent = user_agent or 'CrewAI RAG WebLoader/1.0'
        logger.info(f"Initialized WebLoader with timeout={timeout}")
    
    def load(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Load a document from a URL.
        
        Args:
            source: URL to load.
            **kwargs: Additional arguments:
                - include_images: Whether to include image alt text (default: False)
                - extract_links: Whether to extract links (default: False)
        
        Returns:
            Dict[str, Any]: The loaded document.
        """
        include_images = kwargs.get('include_images', False)
        extract_links = kwargs.get('extract_links', False)
        
        try:
            # Validate URL
            parsed_url = urlparse(source)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {source}")
            
            # Set up headers
            headers = {
                'User-Agent': self.user_agent
            }
            
            # Make HTTP request
            response = requests.get(source, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator='\n', strip=True)
            
            # Extract title
            title = soup.title.string if soup.title else ''
            
            # Extract metadata
            metadata = {
                'source': source,
                'title': title,
                'url': source,
                'content_type': response.headers.get('Content-Type', ''),
                'last_modified': response.headers.get('Last-Modified', ''),
                'source_type': 'web'
            }
            
            # Extract image alt text if requested
            if include_images:
                images = []
                for img in soup.find_all('img'):
                    alt_text = img.get('alt', '')
                    if alt_text:
                        images.append(alt_text)
                
                if images:
                    text += '\n\nImage descriptions:\n' + '\n'.join(images)
                    metadata['has_images'] = True
                    metadata['image_count'] = len(images)
            
            # Extract links if requested
            if extract_links:
                links = []
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    if href and link_text:
                        links.append(f"{link_text}: {href}")
                
                if links:
                    metadata['links'] = links
                    metadata['link_count'] = len(links)
            
            # Generate document ID
            doc_id = f"web_{hashlib.md5(source.encode()).hexdigest()}"
            
            logger.info(f"Loaded web page: {source}")
            return {
                'id': doc_id,
                'text': text,
                'metadata': metadata
            }
        except Exception as e:
            logger.error(f"Error loading web page: {source}", error=str(e))
            # Return empty document with error metadata
            return {
                'id': f"web_{hashlib.md5(source.encode()).hexdigest()}",
                'text': '',
                'metadata': {
                    'source': source,
                    'error': str(e),
                    'source_type': 'web'
                }
            }
    
    def load_batch(self, sources: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Load multiple documents from URLs.
        
        Args:
            sources: List of URLs to load.
            **kwargs: Additional arguments passed to load().
        
        Returns:
            List[Dict[str, Any]]: List of loaded documents.
        """
        documents = []
        
        for source in sources:
            # Add delay between requests to avoid rate limiting
            if documents:
                time.sleep(1)
            
            document = self.load(source, **kwargs)
            documents.append(document)
        
        logger.info(f"Loaded {len(documents)} web pages")
        return documents
    
    def supports(self, source_type: str) -> bool:
        """
        Check if the loader supports a source type.
        
        Args:
            source_type: Type of source.
        
        Returns:
            bool: True if the loader supports the source type, False otherwise.
        """
        return source_type.lower() in ['web', 'url', 'http', 'https']
