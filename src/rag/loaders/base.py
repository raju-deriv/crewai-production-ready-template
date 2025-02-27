from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

class DocumentLoader(ABC):
    """
    Abstract base class for document loaders.
    
    This class defines the interface that all document loaders must implement.
    It provides methods for loading documents from various sources.
    """
    
    @abstractmethod
    def load(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Load a document from a source.
        
        Args:
            source: Source identifier (e.g., file path, URL, message ID).
            **kwargs: Additional arguments specific to the loader.
        
        Returns:
            Dict[str, Any]: The loaded document with at least:
                - 'text': Text content of the document
                - 'metadata': Dictionary of metadata about the document
        """
        pass
    
    @abstractmethod
    def load_batch(self, sources: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Load multiple documents from sources.
        
        Args:
            sources: List of source identifiers.
            **kwargs: Additional arguments specific to the loader.
        
        Returns:
            List[Dict[str, Any]]: List of loaded documents.
        """
        pass
    
    @abstractmethod
    def supports(self, source_type: str) -> bool:
        """
        Check if the loader supports a source type.
        
        Args:
            source_type: Type of source (e.g., 'file', 'url', 'slack').
        
        Returns:
            bool: True if the loader supports the source type, False otherwise.
        """
        pass
