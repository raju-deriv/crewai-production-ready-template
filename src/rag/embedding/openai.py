import structlog
from typing import List, Dict, Any, Optional
from openai import OpenAI
from src.rag.embedding.base import EmbeddingModel
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class OpenAIEmbedding(EmbeddingModel):
    """
    OpenAI embedding model implementation.
    
    This class implements the EmbeddingModel interface for OpenAI embeddings.
    It provides methods for generating embeddings using OpenAI's API.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the OpenAI embedding model.
        
        Args:
            settings: Application settings containing OpenAI configuration.
        """
        self.settings = settings
        self.api_key = settings.openai_api_key
        self._model_name = settings.openai_embedding_model
        self._dimension = 1536  # Default for text-embedding-3-small
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        if settings.openai_api_base:
            self.client.base_url = settings.openai_api_base
            logger.info(f"Using custom OpenAI API base: {settings.openai_api_base}")
    
    def generate(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text using OpenAI.
        
        Args:
            text: The text to generate an embedding for.
        
        Returns:
            List[float]: The embedding vector.
        """
        try:
            response = self.client.embeddings.create(
                model=self._model_name,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {str(e)}")
            # Return a zero vector as fallback
            return [0.0] * self._dimension
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using OpenAI.
        
        Args:
            texts: The texts to generate embeddings for.
        
        Returns:
            List[List[float]]: The embedding vectors.
        """
        try:
            response = self.client.embeddings.create(
                model=self._model_name,
                input=texts
            )
            embeddings = [data.embedding for data in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {str(e)}")
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
