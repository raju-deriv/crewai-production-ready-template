from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, List, Any, Optional, Union
from src.rag.document.processor import DocumentProcessor
from src.rag.vector_db.manager import VectorDBManager
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class DocumentManagementInput(BaseModel):
    """Input schema for DocumentManagementTool."""
    action: str = Field(..., description="The action to perform (list, get, delete)")
    doc_id: Optional[str] = Field(None, description="Document ID for get and delete actions")
    filter: Optional[Dict[str, Any]] = Field(None, description="Filter for list action")
    top_k: Optional[int] = Field(10, description="Number of documents to return for list action")

class DocumentManagementTool(BaseTool):
    name: str = "manage_documents"
    description: str = """
    Manage documents in the knowledge base.
    Use this tool to list, get, or delete documents in the knowledge base.
    """
    args_schema: type[BaseModel] = DocumentManagementInput
    
    # Define settings as a class variable
    _settings: Optional[Settings] = None
    _document_processor: Optional[DocumentProcessor] = None
    _vector_db_manager: Optional[VectorDBManager] = None

    def __init__(self, settings: Settings):
        super().__init__()
        # Store settings in a private attribute
        object.__setattr__(self, "_settings", settings)
        object.__setattr__(self, "_document_processor", DocumentProcessor(settings))
        object.__setattr__(self, "_vector_db_manager", VectorDBManager.get_instance(settings))
        
        logger.info("Initialized DocumentManagementTool")

    def _run(self, action: str, doc_id: Optional[str] = None, 
             filter: Optional[Dict[str, Any]] = None, top_k: Optional[int] = 10) -> str:
        """
        Manage documents in the knowledge base.

        Args:
            action: The action to perform (list, get, delete).
            doc_id: Document ID for get and delete actions.
            filter: Filter for list action.
            top_k: Number of documents to return for list action.

        Returns:
            str: A message indicating the result of the action.
        """
        try:
            # Validate action
            action = action.lower()
            if action not in ['list', 'get', 'delete', 'stats']:
                return f"Unsupported action: {action}. Supported actions: list, get, delete, stats."
            
            # Perform action
            if action == 'list':
                return self._list_documents(filter, top_k)
            elif action == 'get':
                if not doc_id:
                    return "doc_id is required for get action"
                return self._get_document(doc_id)
            elif action == 'delete':
                if not doc_id:
                    return "doc_id is required for delete action"
                return self._delete_document(doc_id)
            elif action == 'stats':
                return self._get_stats()
        
        except Exception as e:
            logger.error(f"Error managing documents: {str(e)}", exc_info=True)
            return f"Error managing documents: {str(e)}"
    
    def _list_documents(self, filter: Optional[Dict[str, Any]] = None, top_k: int = 10) -> str:
        """
        List documents in the knowledge base.

        Args:
            filter: Filter to apply.
            top_k: Number of documents to return.

        Returns:
            str: A message with the list of documents.
        """
        # Create a dummy query to get documents
        dummy_query = [0.0] * self._vector_db_manager.get_connector().dimension
        results = self._vector_db_manager.query(dummy_query, top_k, filter)
        
        if not results:
            return "No documents found"
        
        # Format results
        output = f"Found {len(results)} documents:\n\n"
        
        for i, doc in enumerate(results):
            doc_id = doc.get('id', 'unknown')
            metadata = doc.get('metadata', {})
            text = doc.get('text', '')
            
            # Truncate text if too long
            if len(text) > 100:
                text = text[:100] + "..."
            
            output += f"Document {i+1}:\n"
            output += f"ID: {doc_id}\n"
            
            # Add metadata
            for key, value in metadata.items():
                if key != 'text':  # Skip text in metadata
                    output += f"{key}: {value}\n"
            
            output += f"Text: {text}\n\n"
        
        return output
    
    def _get_document(self, doc_id: str) -> str:
        """
        Get a document from the knowledge base.

        Args:
            doc_id: Document ID.

        Returns:
            str: A message with the document details.
        """
        document = self._document_processor.get_document(doc_id)
        
        if not document:
            return f"Document not found: {doc_id}"
        
        # Format document
        output = f"Document {doc_id}:\n\n"
        
        # Add metadata
        metadata = document.get('metadata', {})
        for key, value in metadata.items():
            if key != 'text':  # Skip text in metadata
                output += f"{key}: {value}\n"
        
        # Add text
        text = document.get('text', '')
        output += f"\nText:\n{text}\n"
        
        return output
    
    def _delete_document(self, doc_id: str) -> str:
        """
        Delete a document from the knowledge base.

        Args:
            doc_id: Document ID.

        Returns:
            str: A message indicating the result of the deletion.
        """
        success = self._document_processor.delete_document(doc_id)
        
        if success:
            return f"Successfully deleted document: {doc_id}"
        else:
            return f"Failed to delete document: {doc_id}"
    
    def _get_stats(self) -> str:
        """
        Get statistics about the knowledge base.

        Returns:
            str: A message with the statistics.
        """
        stats = self._vector_db_manager.get_stats()
        
        if not stats:
            return "Failed to get statistics"
        
        # Format statistics
        output = "Knowledge Base Statistics:\n\n"
        
        # Add vector database type
        output += f"Vector Database: {self._vector_db_manager.get_db_type()}\n"
        
        # Add statistics
        for key, value in stats.items():
            output += f"{key}: {value}\n"
        
        return output
