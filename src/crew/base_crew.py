from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from crewai import Crew
from crewai.tools import BaseTool
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
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name from the crew's agents.
        
        Args:
            tool_name: The name of the tool to retrieve.
            
        Returns:
            The tool if found, None otherwise.
        """
        try:
            # Create the crew to access its agents and tools
            crew = self.create_crew({})
            
            # Iterate through all agents in the crew
            for agent in crew.agents:
                # Iterate through all tools of each agent
                for tool in agent.tools:
                    # Check if the tool name matches
                    if tool.name == tool_name:
                        return tool
            
            # Tool not found
            self.logger.warning(f"Tool '{tool_name}' not found in any agent")
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving tool '{tool_name}'", error=str(e), exc_info=True)
            return None
