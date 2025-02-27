from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

class VectorDBConnector(ABC):
    """
    Abstract base class for vector database connectors.
    
    This class defines the interface that all vector database connectors must implement.
    It provides methods for connecting to a vector database, storing embeddings,
    querying the database, and managing collections.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the vector database.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the vector database.
        
        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def store_embeddings(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Store document embeddings in the vector database.
        
        Args:
            documents: List of documents with embeddings to store.
                Each document should be a dictionary with at least:
                - 'id': Unique identifier for the document
                - 'embedding': Vector embedding of the document
                - 'metadata': Dictionary of metadata about the document
                - 'text': Original text of the document
        
        Returns:
            List[str]: List of document IDs that were successfully stored.
        """
        pass
    
    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector database for similar documents.
        
        Args:
            query_embedding: Vector embedding of the query.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            List[Dict[str, Any]]: List of documents similar to the query.
                Each document is a dictionary with at least:
                - 'id': Unique identifier for the document
                - 'score': Similarity score
                - 'metadata': Dictionary of metadata about the document
                - 'text': Original text of the document
        """
        pass
    
    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the vector database.
        
        Args:
            doc_id: ID of the document to delete.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from the vector database by ID.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        List all collections in the vector database.
        
        Returns:
            List[str]: List of collection names.
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.
        
        Returns:
            Dict[str, Any]: Dictionary of statistics.
        """
        pass
