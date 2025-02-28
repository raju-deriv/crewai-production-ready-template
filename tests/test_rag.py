import pytest
from unittest.mock import Mock, patch
from src.config.settings import Settings
from src.rag.embedding.service import EmbeddingService
from src.rag.vector_db.manager import VectorDBManager
from src.rag.document.processor import DocumentProcessor
from src.rag.query.engine import RAGQueryEngine
from src.tools.rag_query_tool import RAGQueryTool
from src.tools.document_ingestion_tool import DocumentIngestionTool
from src.tools.document_management_tool import DocumentManagementTool
from typing import Dict, List, Any

@pytest.fixture
def settings() -> Settings:
    """Fixture for Settings instance."""
    return Settings()

@pytest.fixture
def mock_embedding_service(settings: Settings):
    """Fixture for a mock EmbeddingService."""
    with patch('src.rag.embedding.service.EmbeddingService.get_instance') as mock:
        mock_instance = Mock()
        mock_instance.generate_embedding.return_value = [0.1] * 1536  # Mock embedding vector
        mock_instance.generate_embeddings.return_value = [[0.1] * 1536]  # Mock embedding vectors
        mock_instance.dimension = 1536
        mock_instance.model_name = "mock-embedding-model"
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_vector_db_manager(settings: Settings):
    """Fixture for a mock VectorDBManager."""
    with patch('src.rag.vector_db.manager.VectorDBManager.get_instance') as mock:
        mock_instance = Mock()
        mock_instance.store_embeddings.return_value = ["doc_123"]
        mock_instance.query.return_value = [
            {
                "id": "doc_123",
                "text": "This is a test document.",
                "metadata": {"source": "test", "source_type": "test"},
                "score": 0.95
            }
        ]
        mock_instance.get_document.return_value = {
            "id": "doc_123",
            "text": "This is a test document.",
            "metadata": {"source": "test", "source_type": "test"}
        }
        mock_instance.delete_document.return_value = True
        mock_instance.get_stats.return_value = {"document_count": 1}
        mock_instance.get_db_type.return_value = "mock-db"
        mock_connector = Mock()
        mock_connector.dimension = 1536
        mock_instance.get_connector.return_value = mock_connector
        mock.return_value = mock_instance
        yield mock_instance

def test_document_processor(settings: Settings, mock_embedding_service, mock_vector_db_manager):
    """Test DocumentProcessor functionality."""
    processor = DocumentProcessor(settings)
    
    # Test processing a document
    doc_ids = processor.process_document("Test document content", {"source": "test"})
    
    # Check that the document was processed
    assert len(doc_ids) > 0
    # The document ID is generated based on the content hash, so we can't predict it exactly
    assert doc_ids[0].startswith("doc_")

def test_rag_query_engine(settings: Settings, mock_embedding_service, mock_vector_db_manager):
    """Test RAGQueryEngine functionality."""
    engine = RAGQueryEngine(settings)
    
    # Test querying
    result = engine.query("Test query")
    
    # Check that the query returned results
    assert "query" in result
    assert "processed_query" in result
    assert "documents" in result
    assert "enhanced_context" in result
    assert len(result["documents"]) > 0
    
    # Verify embedding service was called
    mock_embedding_service.generate_embedding.assert_called()
    
    # Verify vector DB manager was called
    mock_vector_db_manager.query.assert_called()
    
    # Test querying with LLM formatting
    result = engine.query_with_llm("Test query")
    
    # Check that the query returned results with LLM input
    assert "llm_input" in result
    assert "system" in result["llm_input"]
    assert "user" in result["llm_input"]

def test_rag_query_tool(settings: Settings, mock_embedding_service, mock_vector_db_manager):
    """Test RAGQueryTool functionality."""
    tool = RAGQueryTool(settings)
    
    # Test running the tool
    result = tool._run("Test query")
    
    # Check that the tool returned a string result
    assert isinstance(result, str)
    assert "Test query" in result
    assert "Document 1" in result

def test_document_ingestion_tool(settings: Settings, mock_embedding_service, mock_vector_db_manager):
    """Test DocumentIngestionTool functionality."""
    tool = DocumentIngestionTool(settings)
    
    # Mock the web loader
    with patch('src.rag.loaders.web.WebLoader.load') as mock_web_loader:
        mock_web_loader.return_value = {
            "id": "web_123",
            "text": "This is a test web page.",
            "metadata": {"source": "https://example.com", "source_type": "web"}
        }
        
        # Test running the tool with a web source
        result = tool._run("https://example.com", "web")
        
        # Check that the tool returned a success message
        assert isinstance(result, str)
        assert "Successfully ingested" in result
        assert "https://example.com" in result

@pytest.fixture
def mock_role_manager(settings: Settings):
    """Fixture for a mock RoleManager."""
    with patch('src.auth.role_manager.RoleManager') as mock_class:
        mock_instance = Mock()
        # Configure the mock to always return True for permission checks
        mock_instance.has_permission.return_value = True
        mock_instance.can_perform_operation.return_value = True
        mock_instance.is_admin.return_value = True
        mock_class.return_value = mock_instance
        yield mock_instance

def test_document_management_tool(settings: Settings, mock_embedding_service, mock_vector_db_manager, mock_role_manager):
    """Test DocumentManagementTool functionality."""
    # Create a tool with role manager
    tool = DocumentManagementTool(settings, role_manager=mock_role_manager)
    
    # Test listing documents with admin user
    list_result = tool._run("list", user_id="admin_user")
    
    # Check that the tool returned a list of documents
    assert isinstance(list_result, str)
    assert "Found" in list_result
    
    # Test getting a document
    get_result = tool._run("get", doc_id="doc_123", user_id="admin_user")
    
    # Check that the tool returned the document
    assert isinstance(get_result, str)
    assert "Document doc_123" in get_result
    
    # Test deleting a document
    delete_result = tool._run("delete", doc_id="doc_123", user_id="admin_user")
    
    # Check that the tool returned a success message
    assert isinstance(delete_result, str)
    assert "Successfully deleted" in delete_result
    
    # Test getting stats
    stats_result = tool._run("stats", user_id="admin_user")
    
    # Check that the tool returned stats
    assert isinstance(stats_result, str)
    assert "Knowledge Base Statistics" in stats_result
