import structlog
from typing import List, Dict, Any, Optional
import numpy as np
from src.rag.embedding.base import EmbeddingModel
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class SentenceTransformerEmbedding(EmbeddingModel):
    """
    SentenceTransformer embedding model implementation.
    
    This class implements the EmbeddingModel interface for SentenceTransformer embeddings.
    It provides methods for generating embeddings using the sentence-transformers library.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the SentenceTransformer embedding model.
        
        Args:
            settings: Application settings containing SentenceTransformer configuration.
        """
        self.settings = settings
        self._model_name = settings.st_model
        self._model = None
        self._dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Lazy load the model
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Load the SentenceTransformer model.
        """
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            # Update dimension based on the loaded model
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded SentenceTransformer model: {self._model_name} with dimension {self._dimension}")
        except Exception as e:
            logger.error(f"Error loading SentenceTransformer model: {str(e)}")
            self._model = None
    
    def generate(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text using SentenceTransformer.
        
        Args:
            text: The text to generate an embedding for.
        
        Returns:
            List[float]: The embedding vector.
        """
        if self._model is None:
            self._load_model()
            if self._model is None:
                logger.error("SentenceTransformer model not loaded")
                return [0.0] * self._dimension
        
        try:
            embedding = self._model.encode(text)
            # Convert numpy array to list
            embedding_list = embedding.tolist()
            logger.debug(f"Generated embedding with {len(embedding_list)} dimensions")
            return embedding_list
        except Exception as e:
            logger.error(f"Error generating SentenceTransformer embedding: {str(e)}")
            # Return a zero vector as fallback
            return [0.0] * self._dimension
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using SentenceTransformer.
        
        Args:
            texts: The texts to generate embeddings for.
        
        Returns:
            List[List[float]]: The embedding vectors.
        """
        if self._model is None:
            self._load_model()
            if self._model is None:
                logger.error("SentenceTransformer model not loaded")
                return [[0.0] * self._dimension for _ in range(len(texts))]
        
        try:
            embeddings = self._model.encode(texts)
            # Convert numpy arrays to lists
            embeddings_list = embeddings.tolist()
            logger.debug(f"Generated {len(embeddings_list)} embeddings")
            return embeddings_list
        except Exception as e:
            logger.error(f"Error generating SentenceTransformer embeddings: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * self._dimension for _ in range(len(texts))]
    
    @property
    def dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            int: The dimension of the embedding vectors.
        """
        return self._dimension
    
    @property
    def model_name(self) -> str:
        """
        Get the name of the embedding model.
        
        Returns:
            str: The name of the embedding model.
        """
        return self._model_name
