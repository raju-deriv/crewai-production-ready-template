import structlog
import uuid
import os
from typing import Dict, List, Any, Optional, Union
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.rag.vector_db.base import VectorDBConnector
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class ChromaConnector(VectorDBConnector):
    """
    Connector for Chroma vector database.
    
    This class implements the VectorDBConnector interface for Chroma.
    It provides methods for connecting to Chroma, storing embeddings,
    querying the database, and managing collections.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Chroma connector.
        
        Args:
            settings: Application settings containing Chroma configuration.
        """
        self.settings = settings
        self.persist_directory = settings.chroma_persist_dir
        self.collection_name = settings.chroma_collection
        self.client = None
        self.collection = None
        self.is_connected = False
        
        # Create persist directory if it doesn't exist
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory, exist_ok=True)
    
    def connect(self) -> bool:
        """
        Connect to Chroma and initialize the collection.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            # Initialize Chroma client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Connected to existing Chroma collection: {self.collection_name}")
            except Exception as e:
                logger.info(f"Collection {self.collection_name} does not exist, creating it")
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(name=self.collection_name)
                logger.info(f"Created new Chroma collection: {self.collection_name}")
            
            self.is_connected = True
            return True
        except Exception as e:
            logger.error("Failed to connect to Chroma", error=str(e))
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from Chroma.
        
        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        try:
            # Chroma doesn't have an explicit disconnect method
            self.client = None
            self.collection = None
            self.is_connected = False
            logger.info("Disconnected from Chroma")
            return True
        except Exception as e:
            logger.error("Failed to disconnect from Chroma", error=str(e))
            return False
    
    def store_embeddings(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Store document embeddings in Chroma.
        
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
                logger.error("Cannot store embeddings: not connected to Chroma")
                return []
        
        try:
            # Prepare data for Chroma
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.get('id', str(uuid.uuid4()))
                ids.append(doc_id)
                
                # Get embedding
                embeddings.append(doc['embedding'])
                
                # Prepare metadata
                metadata = doc.get('metadata', {})
                metadatas.append(metadata)
                
                # Get document text
                documents_text.append(doc.get('text', ''))
            
            # Add documents to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            logger.info(f"Stored {len(ids)} embeddings in Chroma")
            return ids
        except Exception as e:
            logger.error("Failed to store embeddings in Chroma", error=str(e))
            return []
    
    def query(self, query_embedding: List[float], top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Chroma for similar documents.
        
        Args:
            query_embedding: Vector embedding of the query.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            List[Dict[str, Any]]: List of documents similar to the query.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot query: not connected to Chroma")
                return []
        
        try:
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter,
                include=["metadatas", "documents", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'score': 1.0 - results['distances'][0][i],  # Convert distance to similarity score
                    'metadata': results['metadatas'][0][i],
                    'text': results['documents'][0][i]
                })
            
            logger.info(f"Query returned {len(formatted_results)} results from Chroma")
            return formatted_results
        except Exception as e:
            logger.error("Failed to query Chroma", error=str(e))
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from Chroma.
        
        Args:
            doc_id: ID of the document to delete.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot delete document: not connected to Chroma")
                return False
        
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id} from Chroma")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id} from Chroma", error=str(e))
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from Chroma by ID.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot get document: not connected to Chroma")
                return None
        
        try:
            # Get the document
            result = self.collection.get(
                ids=[doc_id],
                include=["metadatas", "documents", "embeddings"]
            )
            
            if not result['ids']:
                logger.warning(f"Document {doc_id} not found in Chroma")
                return None
            
            return {
                'id': result['ids'][0],
                'embedding': result['embeddings'][0],
                'metadata': result['metadatas'][0],
                'text': result['documents'][0]
            }
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from Chroma", error=str(e))
            return None
    
    def list_collections(self) -> List[str]:
        """
        List all collections in Chroma.
        
        Returns:
            List[str]: List of collection names.
        """
        if not self.client and not self.connect():
            logger.error("Cannot list collections: not connected to Chroma")
            return []
        
        try:
            collections = self.client.list_collections()
            collection_names = [collection.name for collection in collections]
            logger.info(f"Listed {len(collection_names)} collections in Chroma")
            return collection_names
        except Exception as e:
            logger.error("Failed to list collections in Chroma", error=str(e))
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Chroma collection.
        
        Returns:
            Dict[str, Any]: Dictionary of statistics.
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot get stats: not connected to Chroma")
                return {}
        
        try:
            # Get collection count
            count = self.collection.count()
            
            # Get collection info
            stats = {
                'count': count,
                'name': self.collection_name,
                'persist_directory': self.persist_directory
            }
            
            logger.info("Retrieved Chroma collection stats")
            return stats
        except Exception as e:
            logger.error("Failed to get Chroma collection stats", error=str(e))
            return {}
