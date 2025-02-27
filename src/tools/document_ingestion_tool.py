from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, List, Any, Optional, Union
from src.rag.document.processor import DocumentProcessor
from src.rag.loaders.web import WebLoader
from src.rag.loaders.file import FileLoader
from src.rag.loaders.slack import SlackLoader
from src.config.settings import Settings
import os
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)

class DocumentIngestionInput(BaseModel):
    """Input schema for DocumentIngestionTool."""
    source: str = Field(..., description="The source to ingest (URL, file path, or Slack message/file ID)")
    source_type: str = Field(..., description="The type of source (web, file, slack)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata to associate with the document")
    channel_id: Optional[str] = Field(None, description="Slack channel ID (required for Slack sources)")
    is_file: Optional[bool] = Field(False, description="Whether the Slack source is a file (default: False)")

class DocumentIngestionTool(BaseTool):
    name: str = "ingest_document"
    description: str = """
    Ingest a document into the knowledge base.
    Use this tool to add documents from various sources to the knowledge base.
    Supported source types: web, file, slack.
    """
    args_schema: type[BaseModel] = DocumentIngestionInput
    
    # Define settings as a class variable
    _settings: Optional[Settings] = None
    _document_processor: Optional[DocumentProcessor] = None
    _web_loader: Optional[WebLoader] = None
    _file_loader: Optional[FileLoader] = None
    _slack_loader: Optional[SlackLoader] = None

    def __init__(self, settings: Settings):
        super().__init__()
        # Store settings in a private attribute
        object.__setattr__(self, "_settings", settings)
        object.__setattr__(self, "_document_processor", DocumentProcessor(settings))
        
        # Initialize loaders
        object.__setattr__(self, "_web_loader", WebLoader())
        object.__setattr__(self, "_file_loader", FileLoader())
        object.__setattr__(self, "_slack_loader", SlackLoader(settings))
        
        logger.info("Initialized DocumentIngestionTool")

    def _run(self, source: str, source_type: str, metadata: Optional[Dict[str, Any]] = None, 
             channel_id: Optional[str] = None, is_file: Optional[bool] = False) -> str:
        """
        Ingest a document into the knowledge base.

        Args:
            source: The source to ingest.
            source_type: The type of source.
            metadata: Optional metadata to associate with the document.
            channel_id: Slack channel ID (required for Slack sources).
            is_file: Whether the Slack source is a file.

        Returns:
            str: A message indicating the result of the ingestion.
        """
        try:
            # Validate source type
            source_type = source_type.lower()
            if source_type not in ['web', 'file', 'slack']:
                return f"Unsupported source type: {source_type}. Supported types: web, file, slack."
            
            # Initialize metadata if not provided
            metadata = metadata or {}
            
            # Add source type to metadata
            metadata['source_type'] = source_type
            
            # Load document based on source type
            document = None
            
            if source_type == 'web':
                # Validate URL
                parsed_url = urlparse(source)
                if not parsed_url.scheme or not parsed_url.netloc:
                    return f"Invalid URL: {source}"
                
                document = self._web_loader.load(source)
            
            elif source_type == 'file':
                # Validate file path
                if not os.path.exists(source):
                    return f"File not found: {source}"
                
                document = self._file_loader.load(source)
            
            elif source_type == 'slack':
                # Validate Slack parameters
                if not channel_id:
                    return "channel_id is required for Slack sources"
                
                document = self._slack_loader.load(
                    source,
                    channel_id=channel_id,
                    is_file=is_file
                )
            
            # Check if document was loaded successfully
            if not document or not document.get('text'):
                return f"Failed to load document from {source}"
            
            # Update metadata
            if metadata:
                document['metadata'].update(metadata)
            
            # Process document
            doc_ids = self._document_processor.process_document(document['text'], document['metadata'])
            
            if not doc_ids:
                return f"Failed to process document from {source}"
            
            return f"Successfully ingested document from {source}. Document ID: {doc_ids[0]}"
        
        except Exception as e:
            logger.error(f"Error ingesting document: {str(e)}", exc_info=True)
            return f"Error ingesting document: {str(e)}"
