from crewai import Agent
from typing import Dict, Any
import structlog
from src.config.settings import Settings
from src.tools.rag_query_tool import RAGQueryTool

logger = structlog.get_logger(__name__)

class RAGQueryAgent:
    """Agent that retrieves information from the knowledge base."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rag_query_tool = RAGQueryTool(settings)
        logger.info("Initialized RAGQueryAgent")

    def create(self) -> Agent:
        return Agent(
            role="Knowledge Base Retriever",
            goal="Retrieve relevant information from the knowledge base to answer user queries",
            backstory="""You are an expert at finding and synthesizing information from the 
            organization's knowledge base. You can quickly locate relevant documents and 
            extract the most pertinent information to answer user questions accurately and concisely.""",
            verbose=False,
            allow_delegation=False,
            max_iter=3,
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.rag_query_tool]
        )
