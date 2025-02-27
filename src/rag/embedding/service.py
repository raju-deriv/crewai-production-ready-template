import structlog
from typing import Dict, List, Any, Optional, Type
from src.rag.embedding.base import EmbeddingModel
from src.rag.embedding.openai import OpenAIEmbedding
from src.rag.embedding.sentence_transformers import SentenceTransformerEmbedding
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class EmbeddingService:
    """
    Service for managing embedding models.
    
    This class manages the embedding models and allows switching between them.
    It provides a singleton instance to ensure only one model is active at a time.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, settings: Settings, model_type: Optional[str] = None) -> 'EmbeddingService':
        """
        Get the singleton instance of the EmbeddingService.
        
        Args:
            settings: Application settings.
            model_type: Type of embedding model to use. If None, uses the default from settings.
        
        Returns:
            EmbeddingService: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls(settings, model_type)
        return cls._instance
    
    def __init__(self, settings: Settings, model_type: Optional[str] = None):
        """
        Initialize the EmbeddingService.
        
        Args:
            settings: Application settings.
            model_type: Type of embedding model to use. If None, uses the default from settings.
        """
        self.settings = settings
        self.model_type = model_type or settings.embedding_provider
        self.models: Dict[str, Type[EmbeddingModel]] = {
            'openai': OpenAIEmbedding,
            'sentence_transformers': SentenceTransformerEmbedding
        }
        self.current_model: Optional[EmbeddingModel] = None
        
        # Initialize the default model
        self.set_model(self.model_type)
    
    def set_model(self, model_type: str) -> bool:
        """
        Set the embedding model to use.
        
        Args:
            model_type: Type of embedding model to use.
        
        Returns:
            bool: True if model was set successfully, False otherwise.
        """
        if model_type not in self.models:
            logger.error(f"Unknown embedding model type: {model_type}")
            return False
        
        # Create new model
        try:
            model_class = self.models[model_type]
            self.current_model = model_class(self.settings)
            self.model_type = model_type
            logger.info(f"Set embedding model to: {model_type}")
            return True
        except Exception as e:
            logger.error(f"Error setting embedding model: {model_type}", error=str(e))
            return False
    
    def get_model(self) -> Optional[EmbeddingModel]:
        """
        Get the current embedding model.
        
        Returns:
            Optional[EmbeddingModel]: The current model, or None if not set.
        """
        return self.current_model
    
    def get_model_type(self) -> str:
        """
        Get the current embedding model type.
        
        Returns:
            str: The current embedding model type.
        """
        return self.model_type
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        
        Args:
            text: The text to generate an embedding for.
        
        Returns:
            List[float]: The embedding vector.
        """
        if not self.current_model:
            logger.error("No embedding model available")
            return []
        
        return self.current_model.generate(text)
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: The texts to generate embeddings for.
        
        Returns:
            List[List[float]]: The embedding vectors.
        """
        if not self.current_model:
            logger.error("No embedding model available")
            return []
        
        return self.current_model.generate_batch(texts)
    
    @property
    def dimension(self) -> int:
        """
        Get the dimension of the current embedding model.
        
        Returns:
            int: The dimension of the embedding vectors.
        """
        if not self.current_model:
            logger.error("No embedding model available")
            return 0
        
        return self.current_model.dimension
    
    @property
    def model_name(self) -> str:
        """
        Get the name of the current embedding model.
        
        Returns:
            str: The name of the embedding model.
        """
        if not self.current_model:
            logger.error("No embedding model available")
            return ""
        
        return self.current_model.model_name
