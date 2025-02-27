import structlog
from typing import Dict, List, Any, Optional, Union
from src.rag.query.processor import QueryProcessor
from src.rag.query.enhancer import ContextEnhancer
from src.rag.document.processor import DocumentProcessor
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class RAGQueryEngine:
    """
    Main RAG query engine.
    
    This class coordinates the query processing, document retrieval,
    and context enhancement for RAG.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the RAGQueryEngine.
        
        Args:
            settings: Application settings.
        """
        self.settings = settings
        
        # Initialize components
        self.query_processor = QueryProcessor(expand_queries=True)
        self.context_enhancer = ContextEnhancer(max_context_length=4000)
        self.document_processor = DocumentProcessor(settings)
        
        logger.info("Initialized RAGQueryEngine")
    
    def query(self, query_text: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            query_text: Query text.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
        
        Returns:
            Dict[str, Any]: Query results with:
                - 'query': Original query
                - 'processed_query': Processed query
                - 'documents': Retrieved documents
                - 'enhanced_context': Enhanced context
        """
        # Process query
        processed_query = self.query_processor.process_query(query_text)
        
        # Expand query
        expanded_queries = self.query_processor.expand_query(processed_query)
        
        # Query for each expanded query
        all_results = []
        for expanded_query in expanded_queries:
            results = self.document_processor.query(expanded_query, top_k, filter)
            all_results.extend(results)
        
        # Deduplicate results
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                unique_results.append(result)
        
        # Sort by score
        sorted_results = sorted(unique_results, key=lambda x: x.get('score', 0.0), reverse=True)
        
        # Limit to top_k
        top_results = sorted_results[:top_k]
        
        # Enhance context
        enhanced_context = self.context_enhancer.enhance(query_text, top_results)
        
        logger.info(f"Query returned {len(top_results)} results")
        return {
            'query': query_text,
            'processed_query': processed_query,
            'documents': top_results,
            'enhanced_context': enhanced_context
        }
    
    def query_with_llm(self, query_text: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the RAG system and format for LLM.
        
        Args:
            query_text: Query text.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.
            system_prompt: Optional system prompt to include.
        
        Returns:
            Dict[str, Any]: Query results with:
                - 'query': Original query
                - 'processed_query': Processed query
                - 'documents': Retrieved documents
                - 'enhanced_context': Enhanced context
                - 'llm_input': Formatted input for LLM
        """
        # Query the RAG system
        results = self.query(query_text, top_k, filter)
        
        # Format for LLM
        llm_input = self.context_enhancer.format_for_llm(results['enhanced_context'], system_prompt)
        
        # Add LLM input to results
        results['llm_input'] = llm_input
        
        return results
