from crewai import Agent
import structlog
from src.config.settings import Settings
from src.tools.research_tool import ResearchTool

logger = structlog.get_logger(__name__)

class ResearchAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.research_tool = ResearchTool()

    def create(self) -> Agent:
        return Agent(
            role="Researcher",
            goal="Conduct thorough research on given topics",
            backstory="""You're a skilled researcher with expertise in finding reliable information.
            You can analyze topics deeply and provide comprehensive, well-structured information.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.research_tool]
        )
