import structlog
from typing import Dict, List, Any, Optional, Union
import re

logger = structlog.get_logger(__name__)

class QueryProcessor:
    """
    Processor for queries.
    
    This class provides methods for processing and expanding queries
    to improve retrieval performance.
    """
    
    def __init__(self, expand_queries: bool = True):
        """
        Initialize the QueryProcessor.
        
        Args:
            expand_queries: Whether to expand queries with variations.
        """
        self.expand_queries = expand_queries
        logger.info(f"Initialized QueryProcessor with expand_queries={expand_queries}")
    
    def process_query(self, query: str) -> str:
        """
        Process a query to improve retrieval performance.
        
        Args:
            query: Query to process.
        
        Returns:
            str: Processed query.
        """
        if not query:
            return ""
        
        # Remove extra whitespace
        processed_query = re.sub(r'\s+', ' ', query).strip()
        
        # Remove special characters that might interfere with search
        processed_query = re.sub(r'[^\w\s\?\.]', ' ', processed_query)
        
        # Convert to lowercase
        processed_query = processed_query.lower()
        
        logger.debug(f"Processed query: {processed_query}")
        return processed_query
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand a query with variations to improve retrieval performance.
        
        Args:
            query: Query to expand.
        
        Returns:
            List[str]: List of expanded queries.
        """
        if not query or not self.expand_queries:
            return [query]
        
        # Process the query first
        processed_query = self.process_query(query)
        
        # Start with the original query
        expanded_queries = [processed_query]
        
        # Add variations
        
        # 1. Remove question words
        question_words = ['what', 'who', 'where', 'when', 'why', 'how']
        for word in question_words:
            if processed_query.startswith(word):
                # Remove the question word and any following words like "is", "are", etc.
                without_question = re.sub(f'^{word}\\s+(is|are|was|were|do|does|did)\\s+', '', processed_query)
                if without_question != processed_query:
                    expanded_queries.append(without_question)
        
        # 2. Remove question marks
        if '?' in processed_query:
            expanded_queries.append(processed_query.replace('?', ''))
        
        # 3. Extract key phrases (simple approach)
        words = processed_query.split()
        if len(words) > 3:
            # Take the most important words (skip common words)
            common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about']
            key_words = [word for word in words if word not in common_words]
            if len(key_words) > 2:
                expanded_queries.append(' '.join(key_words))
        
        # Remove duplicates
        expanded_queries = list(dict.fromkeys(expanded_queries))
        
        logger.debug(f"Expanded query to {len(expanded_queries)} variations")
        return expanded_queries
