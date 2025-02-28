from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, List, Any, Optional, Union
from src.rag.document.processor import DocumentProcessor
from src.rag.vector_db.manager import VectorDBManager
from src.config.settings import Settings
from src.auth.role_manager import RoleManager, Operation
from src.auth.permissions import requires_permission
from src.storage.approval_store import ApprovalStore

logger = structlog.get_logger(__name__)

class DocumentManagementInput(BaseModel):
    """Input schema for DocumentManagementTool."""
    action: str = Field(..., description="The action to perform (list, get, delete)")
    doc_id: Optional[str] = Field(None, description="Document ID for get and delete actions")
    filter: Optional[Dict[str, Any]] = Field(None, description="Filter for list action")
    top_k: Optional[int] = Field(10, description="Number of documents to return for list action")
    user_id: Optional[str] = Field(None, description="User ID for permission checks")
    channel_id: Optional[str] = Field(None, description="Channel ID for approval requests")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for approval requests")

class DocumentManagementTool(BaseTool):
    name: str = "manage_documents"
    description: str = """
    Manage documents in the knowledge base with role-based access control.
    Use this tool to list, get, or delete documents in the knowledge base.
    Operations require appropriate permissions and may trigger approval requests.
    
    Required permissions:
    - list: DOCUMENT_LIST permission
    - get: DOCUMENT_VIEW permission
    - delete: DOCUMENT_DELETE permission
    - stats: DOCUMENT_STATS permission
    
    Include user_id, channel_id, and thread_ts for permission checks and approval requests.
    """
    args_schema: type[BaseModel] = DocumentManagementInput
    
    # Define settings as a class variable
    _settings: Optional[Settings] = None
    _document_processor: Optional[DocumentProcessor] = None
    _vector_db_manager: Optional[VectorDBManager] = None

    def __init__(self, settings: Settings, role_manager: Optional[RoleManager] = None, 
                 approval_store: Optional[ApprovalStore] = None):
        super().__init__()
        # Store settings in a private attribute
        object.__setattr__(self, "_settings", settings)
        object.__setattr__(self, "_document_processor", DocumentProcessor(settings))
        object.__setattr__(self, "_vector_db_manager", VectorDBManager.get_instance(settings))
        object.__setattr__(self, "_role_manager", role_manager)
        object.__setattr__(self, "_approval_store", approval_store)
        
        logger.info("Initialized DocumentManagementTool")

    def _run(self, action: str, doc_id: Optional[str] = None, 
             filter: Optional[Dict[str, Any]] = None, top_k: Optional[int] = 10,
             user_id: Optional[str] = None, channel_id: Optional[str] = None,
             thread_ts: Optional[str] = None) -> str:
        """
        Manage documents in the knowledge base.

        Args:
            action: The action to perform (list, get, delete).
            doc_id: Document ID for get and delete actions.
            filter: Filter for list action.
            top_k: Number of documents to return for list action.
            user_id: User ID for permission checks.
            channel_id: Channel ID for approval requests.
            thread_ts: Thread timestamp for approval requests.

        Returns:
            str: A message indicating the result of the action.
        """
        try:
            # Validate action
            action = action.lower()
            if action not in ['list', 'get', 'delete', 'stats']:
                return f"Unsupported action: {action}. Supported actions: list, get, delete, stats."
            
            # Check permissions if role manager is available
            if self._role_manager and user_id:
                # Map action to operation
                operation_map = {
                    'list': Operation.DOCUMENT_LIST,
                    'get': Operation.DOCUMENT_VIEW,
                    'delete': Operation.DOCUMENT_DELETE,
                    'stats': Operation.DOCUMENT_STATS
                }
                
                operation = operation_map.get(action)
                if operation:
                    # Check if user has permission
                    if not self._role_manager.has_permission(user_id, operation):
                        # If approval store is available, create an approval request
                        if self._approval_store and channel_id and thread_ts:
                            details = {
                                'action': action,
                                'doc_id': doc_id,
                                'filter': filter,
                                'top_k': top_k
                            }
                            
                            # Create approval request
                            request_id = self._approval_store.create_request(
                                user_id=user_id,
                                operation=operation,
                                details=details,
                                channel_id=channel_id,
                                thread_ts=thread_ts
                            )
                            
                            return f"You don't have permission to perform this action. An approval request has been sent to administrators. Request ID: {request_id}"
                        else:
                            return f"You don't have permission to perform this action: {action}"
            
            # Perform action
            if action == 'list':
                return self._list_documents(filter, top_k, role_manager=self._role_manager, user_id=user_id)
            elif action == 'get':
                if not doc_id:
                    return "doc_id is required for get action"
                return self._get_document(doc_id, role_manager=self._role_manager, user_id=user_id)
            elif action == 'delete':
                if not doc_id:
                    return "doc_id is required for delete action"
                return self._delete_document(doc_id, role_manager=self._role_manager, user_id=user_id)
            elif action == 'stats':
                return self._get_stats(role_manager=self._role_manager, user_id=user_id)
        
        except Exception as e:
            logger.error(f"Error managing documents: {str(e)}", exc_info=True)
            return f"Error managing documents: {str(e)}"
    
    @requires_permission(Operation.DOCUMENT_LIST)
    def _list_documents(self, filter: Optional[Dict[str, Any]] = None, top_k: int = 10, 
                        role_manager: Optional[RoleManager] = None, user_id: Optional[str] = None) -> str:
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
    
    @requires_permission(Operation.DOCUMENT_VIEW)
    def _get_document(self, doc_id: str, role_manager: Optional[RoleManager] = None, 
                      user_id: Optional[str] = None) -> str:
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
    
    @requires_permission(Operation.DOCUMENT_DELETE)
    def _delete_document(self, doc_id: str, role_manager: Optional[RoleManager] = None, 
                         user_id: Optional[str] = None) -> str:
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
    
    @requires_permission(Operation.DOCUMENT_STATS)
    def _get_stats(self, role_manager: Optional[RoleManager] = None, 
                   user_id: Optional[str] = None) -> str:
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
    
    def execute_approved_operation(self, operation: Operation, details: Dict[str, Any]) -> str:
        """
        Execute an operation that has been approved.
        
        Args:
            operation: The operation to execute.
            details: Details of the operation.
            
        Returns:
            str: Result of the operation.
        """
        try:
            # Extract details
            action = details.get('action')
            doc_id = details.get('doc_id')
            filter = details.get('filter')
            top_k = details.get('top_k', 10)
            
            if not action:
                return "Invalid operation details: action is required"
            
            # Execute the operation
            return self._run(
                action=action,
                doc_id=doc_id,
                filter=filter,
                top_k=top_k
            )
            
        except Exception as e:
            logger.error(f"Error executing approved operation: {str(e)}", exc_info=True)
            return f"Error executing approved operation: {str(e)}"
