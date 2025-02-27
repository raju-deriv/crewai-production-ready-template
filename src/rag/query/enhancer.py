import structlog
from typing import Dict, List, Any, Optional, Union

logger = structlog.get_logger(__name__)

class ContextEnhancer:
    """
    Enhancer for query context.
    
    This class provides methods for enhancing the context with retrieved documents
    to improve the quality of responses.
    """
    
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize the ContextEnhancer.
        
        Args:
            max_context_length: Maximum length of the enhanced context in characters.
        """
        self.max_context_length = max_context_length
        logger.info(f"Initialized ContextEnhancer with max_context_length={max_context_length}")
    
    def enhance(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Enhance the context with retrieved documents.
        
        Args:
            query: Original query.
            retrieved_docs: List of retrieved documents.
        
        Returns:
            str: Enhanced context.
        """
        if not retrieved_docs:
            return f"Query: {query}\n\nNo relevant documents found."
        
        # Start with the query
        context = f"Query: {query}\n\n"
        context += "Relevant information:\n\n"
        
        # Add retrieved documents
        for i, doc in enumerate(retrieved_docs):
            # Extract document text and metadata
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            score = doc.get('score', 0.0)
            
            # Format document information
            doc_info = f"Document {i+1} (Score: {score:.2f}):\n"
            
            # Add source information if available
            source = metadata.get('source', '')
            if source:
                doc_info += f"Source: {source}\n"
            
            # Add title if available
            title = metadata.get('title', '')
            if title:
                doc_info += f"Title: {title}\n"
            
            # Add document text
            doc_info += f"Content: {text}\n\n"
            
            # Check if adding this document would exceed the maximum context length
            if len(context + doc_info) > self.max_context_length:
                # Truncate the document text to fit within the maximum context length
                available_length = self.max_context_length - len(context) - len(doc_info) + len(text)
                if available_length > 100:  # Only add if we can include a meaningful amount of text
                    truncated_text = text[:available_length] + "..."
                    doc_info = doc_info.replace(f"Content: {text}", f"Content: {truncated_text}")
                    context += doc_info
                break
            
            context += doc_info
        
        logger.debug(f"Enhanced context with {len(retrieved_docs)} documents")
        return context
    
    def format_for_llm(self, enhanced_context: str, system_prompt: Optional[str] = None) -> Dict[str, str]:
        """
        Format the enhanced context for an LLM.
        
        Args:
            enhanced_context: Enhanced context.
            system_prompt: Optional system prompt to include.
        
        Returns:
            Dict[str, str]: Formatted context for an LLM.
        """
        default_system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
If the context doesn't contain the information needed to answer the question, say so. 
Don't make up information that isn't in the context."""
        
        system = system_prompt or default_system_prompt
        
        return {
            "system": system,
            "user": enhanced_context
        }
