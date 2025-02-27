import structlog
import time
import uuid
from typing import Dict, List, Any, Optional, Union
import pinecone
from src.rag.vector_db.base import VectorDBConnector
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class PineconeConnector(VectorDBConnector):
    """
    Connector for Pinecone vector database.
    
    This class implements the VectorDBConnector interface for Pinecone.
    It provides methods for connecting to Pinecone, storing embeddings,
    querying the database, and managing collections.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Pinecone connector.
        
        Args:
            settings: Application settings containing Pinecone configuration.
        """
        self.settings = settings
        self.api_key = settings.pinecone_api_key
        self.environment = settings.pinecone_environment
        self.index_name = settings.pinecone_index
        self.index = None
        self.is_connected = False
        
        if not self.api_key or not self.environment:
            logger.warning("Pinecone API key or environment not set")
    
    def connect(self) -> bool:
        """
        Connect to Pinecone and initialize the index.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            # Initialize Pinecone
            pinecone.init(api_key=self.api_key, environment=self.environment)
            
            # Check if index exists, create it if it doesn't
            if self.index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {self.index_name}")
                pinecone.create_index(
                    name=self.index_name,
                    dimension=1536,  # Default for OpenAI embeddings
                    metric="cosine"
                )
                # Wait for index to be ready
                time.sleep(1)
            
            # Connect to the index
            self.index = pinecone.Index(self.index_name)
            self.is_connected = True
            logger.info("Connected to Pinecone", index=self.index_name)
            return True
        except Exception as e:
            logger.error("Failed to connect to Pinecone", error=str(e))
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from Pinecone.
        
        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        try:
            # Pinecone doesn't have an explicit disconnect method
            self.index = None
            self.is_connected = False
            logger.info("Disconnected from Pinecone")
            return True
        except Exception as e:
            logger.error("Failed to disconnect from Pinecone", error=str(e))
            return False
    
    def store_embeddings(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Store document embeddings in Pinecone.
        
        Args:
            documents: List of documents with embeddings to store.
                Each document should be a dictionary with at least:
                - 'id': Unique identifier for the document (optional, will be generated if not provided)
                - 'embedding': Vector embedding of the document
                - 'metadata': Dictionary of metadata about the document
                - 'text': Original text of the document
        
        Returns:
            List[str]: List of document IDs that were successfully stored.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot store embeddings: not connected to Pinecone")
                return []
        
        try:
            # Prepare vectors for upsert
            vectors = []
            doc_ids = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.get('id', str(uuid.uuid4()))
                doc_ids.append(doc_id)
                
                # Prepare metadata
                metadata = doc.get('metadata', {})
                # Add text to metadata for retrieval
                if 'text' in doc and doc['text']:
                    metadata['text'] = doc['text']
                
                # Create vector
                vector = {
                    'id': doc_id,
                    'values': doc['embedding'],
                    'metadata': metadata
                }
                vectors.append(vector)
            
            # Upsert vectors in batches of 100
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Stored {len(vectors)} embeddings in Pinecone")
            return doc_ids
        except Exception as e:
            logger.error("Failed to store embeddings in Pinecone", error=str(e))
            return []
    
    def query(self, query_embedding: List[float], top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Pinecone for similar documents.
        
        Args:
            query_embedding: Vector embedding of the query.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            List[Dict[str, Any]]: List of documents similar to the query.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot query: not connected to Pinecone")
                return []
        
        try:
            # Query the index
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                # Extract text from metadata
                text = match.metadata.get('text', '')
                # Remove text from metadata to avoid duplication
                metadata = {k: v for k, v in match.metadata.items() if k != 'text'}
                
                formatted_results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': metadata,
                    'text': text
                })
            
            logger.info(f"Query returned {len(formatted_results)} results from Pinecone")
            return formatted_results
        except Exception as e:
            logger.error("Failed to query Pinecone", error=str(e))
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from Pinecone.
        
        Args:
            doc_id: ID of the document to delete.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot delete document: not connected to Pinecone")
                return False
        
        try:
            self.index.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id} from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id} from Pinecone", error=str(e))
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from Pinecone by ID.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot get document: not connected to Pinecone")
                return None
        
        try:
            # Fetch the vector
            result = self.index.fetch(ids=[doc_id])
            
            if doc_id not in result.vectors:
                logger.warning(f"Document {doc_id} not found in Pinecone")
                return None
            
            vector = result.vectors[doc_id]
            
            # Extract text from metadata
            text = vector.metadata.get('text', '')
            # Remove text from metadata to avoid duplication
            metadata = {k: v for k, v in vector.metadata.items() if k != 'text'}
            
            return {
                'id': doc_id,
                'embedding': vector.values,
                'metadata': metadata,
                'text': text
            }
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from Pinecone", error=str(e))
            return None
    
    def list_collections(self) -> List[str]:
        """
        List all indexes in Pinecone.
        
        Returns:
            List[str]: List of index names.
        """
        try:
            indexes = pinecone.list_indexes()
            logger.info(f"Listed {len(indexes)} indexes in Pinecone")
            return indexes
        except Exception as e:
            logger.error("Failed to list indexes in Pinecone", error=str(e))
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index.
        
        Returns:
            Dict[str, Any]: Dictionary of statistics.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot get stats: not connected to Pinecone")
                return {}
        
        try:
            stats = self.index.describe_index_stats()
            logger.info("Retrieved Pinecone index stats")
            return stats
        except Exception as e:
            logger.error("Failed to get Pinecone index stats", error=str(e))
            return {}
