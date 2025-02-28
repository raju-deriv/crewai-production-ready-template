from crewai import Agent
from typing import Dict, Any
import structlog
from src.config.settings import Settings
from src.tools.document_ingestion_tool import DocumentIngestionTool
from src.tools.document_management_tool import DocumentManagementTool

logger = structlog.get_logger(__name__)

class DocumentManagementAgent:
    """Agent that manages documents in the knowledge base."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.document_ingestion_tool = DocumentIngestionTool(settings)
        self.document_management_tool = DocumentManagementTool(settings)
        logger.info("Initialized DocumentManagementAgent")

    def create(self) -> Agent:
        return Agent(
            role="Knowledge Base Manager",
            goal="Manage the organization's knowledge base by adding, retrieving, or removing documents",
            backstory="""You are responsible for maintaining the organization's knowledge base.
            You can ingest documents from various sources, organize them effectively, and ensure
            the knowledge base remains up-to-date and relevant. You understand how to process
            different types of documents and extract valuable information from them.""",
            verbose=False,
            allow_delegation=False,
            max_iter=3,
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.document_ingestion_tool, self.document_management_tool]
        )
