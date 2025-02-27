import structlog
from typing import Dict, Optional, Type, Any
from src.rag.vector_db.base import VectorDBConnector
from src.rag.vector_db.pinecone_db import PineconeConnector
from src.rag.vector_db.chroma_db import ChromaConnector
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class VectorDBManager:
    """
    Manager for vector database connectors.
    
    This class manages the vector database connectors and allows switching between them.
    It provides a singleton instance to ensure only one connection is active at a time.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, settings: Settings, db_type: Optional[str] = None) -> 'VectorDBManager':
        """
        Get the singleton instance of the VectorDBManager.
        
        Args:
            settings: Application settings.
            db_type: Type of vector database to use. If None, uses the default from settings.
        
        Returns:
            VectorDBManager: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls(settings, db_type)
        return cls._instance
    
    def __init__(self, settings: Settings, db_type: Optional[str] = None):
        """
        Initialize the VectorDBManager.
        
        Args:
            settings: Application settings.
            db_type: Type of vector database to use. If None, uses the default from settings.
        """
        self.settings = settings
        self.db_type = db_type or settings.vector_db_provider
        self.connectors: Dict[str, Type[VectorDBConnector]] = {
            'pinecone': PineconeConnector,
            'chroma': ChromaConnector
        }
        self.current_connector: Optional[VectorDBConnector] = None
        
        # Initialize the default connector
        self.switch_db(self.db_type)
    
    def switch_db(self, db_type: str) -> bool:
        """
        Switch to a different vector database.
        
        Args:
            db_type: Type of vector database to switch to.
        
        Returns:
            bool: True if switch was successful, False otherwise.
        """
        if db_type not in self.connectors:
            logger.error(f"Unknown vector database type: {db_type}")
            return False
        
        # Disconnect from current connector if it exists
        if self.current_connector:
            self.current_connector.disconnect()
        
        # Create new connector
        try:
            connector_class = self.connectors[db_type]
            self.current_connector = connector_class(self.settings)
            self.db_type = db_type
            
            # Connect to the new database
            success = self.current_connector.connect()
            if success:
                logger.info(f"Switched to vector database: {db_type}")
            else:
                logger.error(f"Failed to connect to vector database: {db_type}")
            
            return success
        except Exception as e:
            logger.error(f"Error switching to vector database: {db_type}", error=str(e))
            return False
    
    def get_connector(self) -> Optional[VectorDBConnector]:
        """
        Get the current vector database connector.
        
        Returns:
            Optional[VectorDBConnector]: The current connector, or None if not connected.
        """
        return self.current_connector
    
    def get_db_type(self) -> str:
        """
        Get the current vector database type.
        
        Returns:
            str: The current vector database type.
        """
        return self.db_type
    
    def store_embeddings(self, documents: list) -> list:
        """
        Store document embeddings in the current vector database.
        
        Args:
            documents: List of documents with embeddings to store.
        
        Returns:
            list: List of document IDs that were successfully stored.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return []
        
        return self.current_connector.store_embeddings(documents)
    
    def query(self, query_embedding: list, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> list:
        """
        Query the current vector database for similar documents.
        
        Args:
            query_embedding: Vector embedding of the query.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            list: List of documents similar to the query.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return []
        
        return self.current_connector.query(query_embedding, top_k, filter)
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the current vector database.
        
        Args:
            doc_id: ID of the document to delete.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return False
        
        return self.current_connector.delete_document(doc_id)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from the current vector database by ID.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return None
        
        return self.current_connector.get_document(doc_id)
    
    def list_collections(self) -> list:
        """
        List all collections in the current vector database.
        
        Returns:
            list: List of collection names.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return []
        
        return self.current_connector.list_collections()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current vector database.
        
        Returns:
            Dict[str, Any]: Dictionary of statistics.
        """
        if not self.current_connector:
            logger.error("No vector database connector available")
            return {}
        
        return self.current_connector.get_stats()
