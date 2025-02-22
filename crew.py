from crewai import Crew, Process
from config.settings import Settings
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from tasks.research_task import create_research_task
from tasks.writing_task import create_writing_task
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchWritingCrew:
    """Crew that handles research and writing tasks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.research_agent = ResearchAgent(settings)
        self.writing_agent = WritingAgent(settings)

    def run(self, topic: str) -> str:
        """Execute the crew workflow for a given topic."""
        try:
            research_task = create_research_task(self.research_agent, topic)
            writing_task = create_writing_task(self.writing_agent, "{result of research task}")

            crew = Crew(
                agents=[self.research_agent.create(), self.writing_agent.create()],
                tasks=[research_task, writing_task],
                process=Process.sequential,
                verbose=False
            )

            result = crew.kickoff()
            logger.info("Crew completed successfully")
            return str(result)
        except Exception as e:
            logger.error(f"Error running crew: {str(e)}")
            raise