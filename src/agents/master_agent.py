from crewai import Agent
from typing import Dict, Any
import structlog
from src.config.settings import Settings
from src.tools.intent_analyzer import IntentAnalyzerTool

logger = structlog.get_logger(__name__)

class MasterAgent:
    """Master agent that analyzes requests and routes them to appropriate agents."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.intent_analyzer = IntentAnalyzerTool()

    def create(self) -> Agent:
        return Agent(
            role="Master Controller",
            goal="Analyze user requests and route them to the most appropriate specialized agent",
            backstory="""You are an intelligent coordinator with expertise in understanding user 
            requests and determining which specialized agent can best handle them. You have deep 
            understanding of each agent's capabilities and can route requests effectively.""",
            verbose=True,
            allow_delegation=True,
            max_iter=3,
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.intent_analyzer]
        )
