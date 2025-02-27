import structlog
import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import time

logger = structlog.get_logger(__name__)

class DocumentCache:
    """
    Cache for processed documents.
    
    This class provides methods for caching processed documents to avoid reprocessing.
    It stores documents in a local directory with a configurable TTL.
    """
    
    def __init__(self, cache_dir: str = "./document_cache", ttl: int = 86400):
        """
        Initialize the DocumentCache.
        
        Args:
            cache_dir: Directory to store cached documents.
            ttl: Time-to-live for cached documents in seconds (default: 1 day).
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"Initialized DocumentCache with cache_dir={cache_dir}, ttl={ttl}")
    
    def _get_cache_path(self, doc_id: str) -> str:
        """
        Get the file path for a cached document.
        
        Args:
            doc_id: ID of the document.
        
        Returns:
            str: File path for the cached document.
        """
        # Hash the doc_id to create a safe filename
        hashed_id = hashlib.md5(doc_id.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed_id}.json")
    
    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from the cache.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found and not expired, None otherwise.
        """
        cache_path = self._get_cache_path(doc_id)
        
        # Check if cache file exists
        if not os.path.exists(cache_path):
            return None
        
        try:
            # Read cache file
            with open(cache_path, 'r') as f:
                cached_doc = json.load(f)
            
            # Check if cache is expired
            cached_time = cached_doc.get('_cached_time', 0)
            if time.time() - cached_time > self.ttl:
                logger.debug(f"Cache expired for document {doc_id}")
                return None
            
            # Remove cache metadata
            if '_cached_time' in cached_doc:
                del cached_doc['_cached_time']
            
            logger.debug(f"Cache hit for document {doc_id}")
            return cached_doc
        except Exception as e:
            logger.error(f"Error reading cache for document {doc_id}", error=str(e))
            return None
    
    def store(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        Store a document in the cache.
        
        Args:
            doc_id: ID of the document to store.
            document: Document to store.
        
        Returns:
            bool: True if document was stored successfully, False otherwise.
        """
        cache_path = self._get_cache_path(doc_id)
        
        try:
            # Add cache metadata
            cached_doc = document.copy()
            cached_doc['_cached_time'] = time.time()
            
            # Write cache file
            with open(cache_path, 'w') as f:
                json.dump(cached_doc, f)
            
            logger.debug(f"Cached document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error caching document {doc_id}", error=str(e))
            return False
    
    def invalidate(self, doc_id: str) -> bool:
        """
        Invalidate a cached document.
        
        Args:
            doc_id: ID of the document to invalidate.
        
        Returns:
            bool: True if document was invalidated successfully, False otherwise.
        """
        cache_path = self._get_cache_path(doc_id)
        
        # Check if cache file exists
        if not os.path.exists(cache_path):
            return True
        
        try:
            # Delete cache file
            os.remove(cache_path)
            logger.debug(f"Invalidated cache for document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for document {doc_id}", error=str(e))
            return False
    
    def clear(self) -> bool:
        """
        Clear all cached documents.
        
        Returns:
            bool: True if cache was cleared successfully, False otherwise.
        """
        try:
            # Delete all files in cache directory
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            logger.info("Cleared document cache")
            return True
        except Exception as e:
            logger.error("Error clearing document cache", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dict[str, Any]: Dictionary of statistics.
        """
        try:
            # Count files in cache directory
            file_count = 0
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                'file_count': file_count,
                'total_size_bytes': total_size,
                'cache_dir': self.cache_dir,
                'ttl': self.ttl
            }
        except Exception as e:
            logger.error("Error getting cache stats", error=str(e))
            return {
                'error': str(e)
            }
