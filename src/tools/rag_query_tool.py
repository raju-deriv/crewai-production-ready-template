from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, List, Any, Optional, Union
from src.rag.query.engine import RAGQueryEngine
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class RAGQueryInput(BaseModel):
    """Input schema for RAGQueryTool."""
    query: str = Field(..., description="The query to search for in the knowledge base")
    top_k: int = Field(5, description="Number of results to return")
    filter: Optional[Dict[str, Any]] = Field(None, description="Optional filter to apply to the query")

class RAGQueryTool(BaseTool):
    name: str = "rag_query"
    description: str = """
    Query the knowledge base for information.
    Use this tool to search for information in the knowledge base.
    The tool will return relevant documents and an enhanced context.
    """
    args_schema: type[BaseModel] = RAGQueryInput
    
    # Define settings as a class variable
    _settings: Optional[Settings] = None
    _query_engine: Optional[RAGQueryEngine] = None

    def __init__(self, settings: Settings):
        super().__init__()
        # Store settings in a private attribute
        object.__setattr__(self, "_settings", settings)
        object.__setattr__(self, "_query_engine", RAGQueryEngine(settings))
        logger.info("Initialized RAGQueryTool")

    def _run(self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> str:
        """
        Query the knowledge base.

        Args:
            query: The query to search for.
            top_k: Number of results to return.
            filter: Optional filter to apply to the query.

        Returns:
            str: The enhanced context with retrieved documents.
        """
        try:
            # Query the RAG system
            results = self._query_engine.query(query, top_k, filter)
            
            # Return the enhanced context
            return results['enhanced_context']
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
            return f"Error querying knowledge base: {str(e)}"
