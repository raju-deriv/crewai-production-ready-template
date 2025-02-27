from abc import ABC, abstractmethod
from typing import List, Union

class EmbeddingModel(ABC):
    """
    Abstract base class for embedding models.
    
    This class defines the interface that all embedding models must implement.
    It provides methods for generating embeddings for text.
    """
    
    @abstractmethod
    def generate(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        
        Args:
            text: The text to generate an embedding for.
        
        Returns:
            List[float]: The embedding vector.
        """
        pass
    
    @abstractmethod
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: The texts to generate embeddings for.
        
        Returns:
            List[List[float]]: The embedding vectors.
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            int: The dimension of the embedding vectors.
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Get the name of the embedding model.
        
        Returns:
            str: The name of the embedding model.
        """
        pass
