import structlog
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Union
from src.rag.document.chunker import TextChunker
from src.rag.document.cache import DocumentCache
from src.rag.embedding.service import EmbeddingService
from src.rag.vector_db.manager import VectorDBManager
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class DocumentProcessor:
    """
    Main document processing pipeline.
    
    This class coordinates the document processing pipeline, including:
    - Chunking documents
    - Generating embeddings
    - Storing documents in the vector database
    - Caching processed documents
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the DocumentProcessor.
        
        Args:
            settings: Application settings.
        """
        self.settings = settings
        
        # Initialize components
        self.chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        self.cache = None
        if settings.cache_enabled:
            self.cache = DocumentCache(
                cache_dir=settings.cache_dir,
                ttl=settings.redis_ttl  # Reuse Redis TTL for document cache
            )
        
        self.embedding_service = EmbeddingService.get_instance(settings)
        self.vector_db_manager = VectorDBManager.get_instance(settings)
        
        logger.info("Initialized DocumentProcessor")
    
    def _generate_document_id(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Generate a unique ID for a document based on its content and metadata.
        
        Args:
            text: Text content of the document.
            metadata: Metadata about the document.
        
        Returns:
            str: Unique ID for the document.
        """
        # Create a string representation of the metadata
        metadata_str = str(sorted(metadata.items()))
        
        # Create a hash of the text and metadata
        content_hash = hashlib.md5((text + metadata_str).encode()).hexdigest()
        
        return f"doc_{content_hash}"
    
    def process_document(self, text: str, metadata: Dict[str, Any] = None) -> List[str]:
        """
        Process a single document.
        
        Args:
            text: Text content of the document.
            metadata: Metadata about the document.
        
        Returns:
            List[str]: List of document IDs that were processed and stored.
        """
        if not text:
            logger.warning("Empty document text, skipping processing")
            return []
        
        metadata = metadata or {}
        
        # Generate document ID
        doc_id = self._generate_document_id(text, metadata)
        
        # Check cache if enabled
        if self.cache:
            cached_doc = self.cache.get(doc_id)
            if cached_doc:
                logger.info(f"Using cached document {doc_id}")
                return [doc_id]
        
        # Create document
        document = {
            'id': doc_id,
            'text': text,
            'metadata': metadata
        }
        
        # Process document
        return self.process_documents([document])
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Process multiple documents.
        
        Args:
            documents: List of documents to process.
                Each document should be a dictionary with at least:
                - 'text': Text content of the document
                - 'metadata': Dictionary of metadata about the document
        
        Returns:
            List[str]: List of document IDs that were processed and stored.
        """
        if not documents:
            logger.warning("Empty document list, skipping processing")
            return []
        
        # Step 1: Chunk documents
        logger.debug(f"Chunking {len(documents)} documents")
        chunked_docs = self.chunker.chunk_documents(documents)
        
        # Step 2: Generate embeddings
        logger.debug(f"Generating embeddings for {len(chunked_docs)} document chunks")
        texts = [doc['text'] for doc in chunked_docs]
        embeddings = self.embedding_service.generate_embeddings(texts)
        
        # Step 3: Add embeddings to documents
        for i, embedding in enumerate(embeddings):
            chunked_docs[i]['embedding'] = embedding
        
        # Step 4: Store documents in vector database
        logger.debug(f"Storing {len(chunked_docs)} document chunks in vector database")
        doc_ids = self.vector_db_manager.store_embeddings(chunked_docs)
        
        # Step 5: Cache processed documents if enabled
        if self.cache:
            for doc in documents:
                if 'id' in doc:
                    self.cache.store(doc['id'], doc)
        
        logger.info(f"Processed {len(documents)} documents into {len(doc_ids)} chunks")
        return doc_ids
    
    def query(self, query_text: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector database for similar documents.
        
        Args:
            query_text: Query text.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            List[Dict[str, Any]]: List of documents similar to the query.
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Query vector database
        results = self.vector_db_manager.query(query_embedding, top_k, filter)
        
        logger.info(f"Query returned {len(results)} results")
        return results
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the vector database and cache.
        
        Args:
            doc_id: ID of the document to delete.
        
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        # Delete from vector database
        success = self.vector_db_manager.delete_document(doc_id)
        
        # Delete from cache if enabled
        if self.cache:
            self.cache.invalidate(doc_id)
        
        logger.info(f"Deleted document {doc_id}")
        return success
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document from the vector database or cache.
        
        Args:
            doc_id: ID of the document to retrieve.
        
        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise.
        """
        # Check cache first if enabled
        if self.cache:
            cached_doc = self.cache.get(doc_id)
            if cached_doc:
                logger.debug(f"Cache hit for document {doc_id}")
                return cached_doc
        
        # Get from vector database
        document = self.vector_db_manager.get_document(doc_id)
        
        if document:
            logger.debug(f"Retrieved document {doc_id} from vector database")
        else:
            logger.warning(f"Document {doc_id} not found")
        
        return document
