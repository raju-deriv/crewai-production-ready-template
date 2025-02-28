import structlog
import time
import uuid
from typing import Dict, List, Any, Optional, Union
from pinecone import Pinecone
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
        self.index_name = settings.pinecone_index
        self.pc = None
        self.index = None
        self.is_connected = False
        
        if not self.api_key:
            logger.warning("Pinecone API key not set")
    
    def connect(self) -> bool:
        """
        Connect to Pinecone and initialize the index.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            # Check if API key is set
            if not self.api_key:
                logger.error("Pinecone API key not set")
                self.is_connected = False
                return False
            
            # Initialize Pinecone with detailed logging
            logger.info("Initializing Pinecone")
            self.pc = Pinecone(api_key=self.api_key)
            
            try:
                # List indexes to check connection
                logger.info("Listing Pinecone indexes")
                indexes = self.pc.list_indexes()
                index_names = [index.name for index in indexes]
                logger.info(f"Available Pinecone indexes: {index_names}")
                
                # Check if index exists
                if self.index_name not in index_names:
                    logger.error(f"Pinecone index {self.index_name} does not exist")
                    self.is_connected = False
                    return False
                
                # Get the index configuration
                index_info = next((idx for idx in indexes if idx.name == self.index_name), None)
                if not index_info:
                    logger.error(f"Could not find index info for {self.index_name}")
                    self.is_connected = False
                    return False
                
                # Connect to the index
                logger.info(f"Connecting to Pinecone index: {self.index_name}")
                self.index = self.pc.Index(host=index_info.host)
                self.is_connected = True
                logger.info("Connected to Pinecone", index=self.index_name)
                return True
            except Exception as inner_e:
                logger.error("Failed to access Pinecone indexes", error=str(inner_e))
                self.is_connected = False
                return False
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
            self.pc = None
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
                metadata = doc.get('metadata', {}).copy()
                
                # Flatten nested metadata for Pinecone (it only supports simple types)
                flattened_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, dict):
                        # Convert nested dict to flat keys
                        for sub_key, sub_value in value.items():
                            flattened_metadata[f"{key}_{sub_key}"] = sub_value
                    elif isinstance(value, (str, int, float, bool)) or (isinstance(value, list) and all(isinstance(x, str) for x in value)):
                        # Keep simple types as is
                        flattened_metadata[key] = value
                    else:
                        # Convert other types to string
                        flattened_metadata[key] = str(value)
                
                # Add text to metadata for retrieval
                if 'text' in doc and doc['text']:
                    flattened_metadata['text'] = doc['text']
                
                # Create vector
                vector = {
                    'id': doc_id,
                    'values': doc['embedding'],
                    'metadata': flattened_metadata
                }
                vectors.append(vector)
            
            # Upsert vectors in batches of 100
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                self.index.upsert(
                    vectors=batch,
                    namespace="default"
                )
            
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
                namespace="default",
                vector=query_embedding,
                top_k=top_k,
                include_values=True,
                include_metadata=True,
                filter=filter
            )
            
            # Format results
            formatted_results = []
            for match in results['matches']:
                # Extract text from metadata
                text = match['metadata'].get('text', '')
                # Remove text from metadata to avoid duplication
                metadata = {k: v for k, v in match['metadata'].items() if k != 'text'}
                
                formatted_results.append({
                    'id': match['id'],
                    'score': match['score'],
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
            self.index.delete(
                ids=[doc_id],
                namespace="default"
            )
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
            result = self.index.fetch(
                ids=[doc_id],
                namespace="default"
            )
            
            # In Pinecone v6, the fetch response is a FetchResponse object with a vectors attribute
            if hasattr(result, 'vectors') and hasattr(result.vectors, 'get'):
                vector_data = result.vectors.get(doc_id)
                if vector_data:
                    # Extract text from metadata
                    text = vector_data.metadata.get('text', '')
                    # Remove text from metadata to avoid duplication
                    metadata = {k: v for k, v in vector_data.metadata.items() if k != 'text'}
                    
                    return {
                        'id': doc_id,
                        'embedding': vector_data.values,
                        'metadata': metadata,
                        'text': text
                    }
            
            # If we get here, we couldn't find the document
            logger.warning(f"Document {doc_id} not found in Pinecone")
            return None
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
            if not self.pc:
                if not self.connect():
                    return []
            
            indexes = self.pc.list_indexes()
            index_names = [index.name for index in indexes]
            logger.info(f"Listed {len(index_names)} indexes in Pinecone")
            return index_names
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
