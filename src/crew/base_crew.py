from abc import ABC, abstractmethod
from crewai import Crew
from src.config.settings import Settings
import structlog

logger = structlog.get_logger(__name__)

class BaseCrew(ABC):
    """Abstract base class for CrewAI crews."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    def create_crew(self, inputs: dict[str, str]) -> Crew:
        """Create and configure the CrewAI crew."""
        pass

    def run(self, inputs: dict[str, str]) -> str:
        """Execute the crew with the given inputs."""
        try:
            crew = self.create_crew(inputs)
            result = crew.kickoff()
            self.logger.info("Crew executed successfully", inputs=inputs)
            return str(result)
        except Exception as e:
            self.logger.error("Error running crew", error=str(e), exc_info=True)
            raise