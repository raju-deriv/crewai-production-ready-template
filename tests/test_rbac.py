"""
Test module for role-based access control in DocumentManagementTool.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.config.settings import Settings
from src.auth.role_manager import RoleManager, Operation, Role
from src.storage.approval_store import ApprovalStore
from src.tools.document_management_tool import DocumentManagementTool

@pytest.fixture
def settings() -> Settings:
    """Fixture for Settings instance."""
    settings = MagicMock(spec=Settings)
    settings.admin_user_ids = ["U123ADMIN"]
    
    # Add required attributes for DocumentProcessor
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.cache_enabled = False
    settings.redis_ttl = 86400
    settings.embedding_provider = "openai"
    settings.openai_embedding_model = "text-embedding-3-small"
    settings.vector_db_provider = "pinecone"
    
    return settings

@pytest.fixture
def role_manager(settings: Settings) -> RoleManager:
    """Fixture for RoleManager with mocked permissions."""
    role_manager = RoleManager(settings)
    
    # Define test user IDs
    admin_user_id = "U123ADMIN"
    editor_user_id = "U123EDITOR"
    viewer_user_id = "U123VIEWER"
    
    # Override admin_user_ids for testing
    role_manager.admin_user_ids = [admin_user_id]
    
    # Mock has_permission method
    role_manager.has_permission = MagicMock()
    
    # Set up permission responses for different user types
    def has_permission_mock(user_id, operation):
        if user_id == admin_user_id:
            # Admin has all permissions
            return True
        elif user_id == editor_user_id:
            # Editor has list, view, stats permissions but not delete
            return operation in [Operation.DOCUMENT_LIST, Operation.DOCUMENT_VIEW, Operation.DOCUMENT_STATS]
        elif user_id == viewer_user_id:
            # Viewer has only list and view permissions
            return operation in [Operation.DOCUMENT_LIST, Operation.DOCUMENT_VIEW]
        else:
            # Unknown users have no permissions
            return False
    
    role_manager.has_permission.side_effect = has_permission_mock
    return role_manager

@pytest.fixture
def approval_store() -> ApprovalStore:
    """Fixture for ApprovalStore."""
    approval_store = MagicMock(spec=ApprovalStore)
    approval_store.create_request.return_value = "test_request_123"
    return approval_store

@pytest.fixture
def doc_tool(settings: Settings, role_manager: RoleManager, approval_store: ApprovalStore) -> DocumentManagementTool:
    """Fixture for DocumentManagementTool with mocked dependencies."""
    # Mock EmbeddingService
    with patch('src.rag.embedding.service.EmbeddingService') as mock_embedding_service_class, \
         patch('src.rag.vector_db.manager.VectorDBManager') as mock_vector_db_class, \
         patch('src.rag.document.processor.DocumentProcessor') as mock_processor_class:
        
        # Create mock instances
        mock_embedding_service = MagicMock()
        mock_vector_db = MagicMock()
        mock_processor = MagicMock()
        
        # Configure mock EmbeddingService
        mock_embedding_service_class.get_instance.return_value = mock_embedding_service
        mock_embedding_service.dimension = 1536
        mock_embedding_service.model_name = "mock-embedding-model"
        mock_embedding_service.generate_embedding.return_value = [0.1] * 1536
        
        # Configure mock VectorDBManager
        mock_vector_db_class.get_instance.return_value = mock_vector_db
        mock_connector = MagicMock()
        mock_connector.dimension = 1536
        mock_vector_db.get_connector.return_value = mock_connector
        mock_vector_db.get_stats.return_value = {"document_count": 10}
        mock_vector_db.get_db_type.return_value = "mock-db"
        
        # Configure mock DocumentProcessor
        mock_processor_class.return_value = mock_processor
        
        # Initialize document management tool with role manager and approval store
        doc_tool = DocumentManagementTool(
            settings=settings,
            role_manager=role_manager,
            approval_store=approval_store
        )
        
        # Replace the document processor with our mock
        object.__setattr__(doc_tool, "_document_processor", mock_processor)
        object.__setattr__(doc_tool, "_vector_db_manager", mock_vector_db)
        
        return doc_tool

def test_admin_permissions(doc_tool: DocumentManagementTool) -> None:
    """Test that admin users have all permissions."""
    admin_user_id = "U123ADMIN"
    
    # Admin should be able to perform all operations
    assert_permission_granted(doc_tool, admin_user_id, "list")
    assert_permission_granted(doc_tool, admin_user_id, "get", doc_id="test_doc")
    assert_permission_granted(doc_tool, admin_user_id, "delete", doc_id="test_doc")
    assert_permission_granted(doc_tool, admin_user_id, "stats")

def test_editor_permissions(doc_tool: DocumentManagementTool) -> None:
    """Test that editor users have limited permissions."""
    editor_user_id = "U123EDITOR"
    
    # Editor should be able to list, get, and view stats
    assert_permission_granted(doc_tool, editor_user_id, "list")
    assert_permission_granted(doc_tool, editor_user_id, "get", doc_id="test_doc")
    assert_permission_granted(doc_tool, editor_user_id, "stats")
    
    # Editor should not be able to delete
    assert_permission_denied(doc_tool, editor_user_id, "delete", doc_id="test_doc")

def test_viewer_permissions(doc_tool: DocumentManagementTool) -> None:
    """Test that viewer users have limited permissions."""
    viewer_user_id = "U123VIEWER"
    
    # Viewer should be able to list and get
    assert_permission_granted(doc_tool, viewer_user_id, "list")
    assert_permission_granted(doc_tool, viewer_user_id, "get", doc_id="test_doc")
    
    # Viewer should not be able to delete or view stats
    assert_permission_denied(doc_tool, viewer_user_id, "delete", doc_id="test_doc")
    assert_permission_denied(doc_tool, viewer_user_id, "stats")

def test_unknown_user_permissions(doc_tool: DocumentManagementTool) -> None:
    """Test that unknown users have no permissions."""
    # Unknown user should not be able to perform any operations
    assert_permission_denied(doc_tool, "UNKNOWN", "list")
    assert_permission_denied(doc_tool, "UNKNOWN", "get", doc_id="test_doc")
    assert_permission_denied(doc_tool, "UNKNOWN", "delete", doc_id="test_doc")
    assert_permission_denied(doc_tool, "UNKNOWN", "stats")

def test_approval_request_creation(doc_tool: DocumentManagementTool, approval_store: ApprovalStore) -> None:
    """Test that approval requests are created when needed."""
    # Set up test parameters
    viewer_user_id = "U123VIEWER"
    action = "delete"
    doc_id = "test_doc"
    channel_id = "C123"
    thread_ts = "1234.5678"
    
    # Viewer trying to delete should trigger approval request
    result = doc_tool._run(
        action=action,
        doc_id=doc_id,
        user_id=viewer_user_id,
        channel_id=channel_id,
        thread_ts=thread_ts
    )
    
    # Check that approval request was created
    approval_store.create_request.assert_called_once()
    assert "approval request has been sent" in result
    assert "test_request_123" in result

def assert_permission_granted(doc_tool: DocumentManagementTool, user_id: str, action: str, **kwargs) -> None:
    """Assert that a user has permission to perform an action."""
    with patch.object(doc_tool, '_list_documents', return_value="List result"), \
         patch.object(doc_tool, '_get_document', return_value="Get result"), \
         patch.object(doc_tool, '_delete_document', return_value="Delete result"), \
         patch.object(doc_tool, '_get_stats', return_value="Stats result"):
        
        result = doc_tool._run(action=action, user_id=user_id, **kwargs)
        
        # Check that the action was performed
        if action == "list":
            assert result == "List result"
        elif action == "get":
            assert result == "Get result"
        elif action == "delete":
            assert result == "Delete result"
        elif action == "stats":
            assert result == "Stats result"

def assert_permission_denied(doc_tool: DocumentManagementTool, user_id: str, action: str, **kwargs) -> None:
    """Assert that a user does not have permission to perform an action."""
    result = doc_tool._run(action=action, user_id=user_id, **kwargs)
    assert "You don't have permission" in result
