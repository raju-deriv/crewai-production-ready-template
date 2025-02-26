from crewai import Crew, Process, Task
from typing import Dict, Any
import structlog
from src.config.settings import Settings
from src.agents.master_agent import MasterAgent
from src.agents.research_agent import ResearchAgent
from src.agents.weather_agent import WeatherAgent
from src.crew.base_crew import BaseCrew

logger = structlog.get_logger(__name__)

class MasterCrew(BaseCrew):
    """Master crew that routes requests to appropriate specialized crews."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.master_agent = MasterAgent(settings)
        self.research_agent = ResearchAgent(settings)
        self.weather_agent = WeatherAgent(settings)

    def create_crew(self, inputs: dict[str, str]) -> Crew:
        """Create a crew with the master agent and appropriate specialized agents."""
        request = inputs.get("topic", "")  # Using 'topic' for backward compatibility
        conversation_history = inputs.get("conversation_history", [])

        # Create the master agent task to analyze intent
        context_info = [
            f"User request: {request}",
            f"Previous conversation context: {self._format_history(conversation_history)}",
            "Determine which specialized agent should handle this request.",
            "Consider the full context and the specific capabilities of each agent.",
            "Return your analysis in JSON format with intent and parameters."
        ]
        
        master_task = Task(
            description=f"Analyze this request and determine which agent should handle it: {request}\n\n{' '.join(context_info)}",
            expected_output="JSON object with intent analysis",
            agent=self.master_agent.create()
        )

        # Create the crew with just the master task initially
        crew = Crew(
            agents=[self.master_agent.create()],
            tasks=[master_task],
            process=Process.sequential,
            verbose=True
        )

        # Get the master agent's decision
        result = crew.kickoff()
        result_str = str(result)
        logger.info("Master agent analysis", result=result_str)

        # Create task for the appropriate specialized agent
        if "weather" in result_str.lower():
            weather_context = [
                "The user wants weather information.",
                f"Previous conversation: {self._format_history(conversation_history)}",
                f"Original request: {request}"
            ]
            
            specialized_task = Task(
                description=f"Get weather information\n\n{' '.join(weather_context)}",
                expected_output="Weather information for the requested location",
                agent=self.weather_agent.create()
            )
            specialized_agent = self.weather_agent
        else:  # Default to research
            research_context = [
                "The user wants information about a topic.",
                f"Previous conversation: {self._format_history(conversation_history)}",
                f"Original request: {request}"
            ]
            
            specialized_task = Task(
                description=f"Research the topic\n\n{' '.join(research_context)}",
                expected_output="Detailed research information about the requested topic",
                agent=self.research_agent.create()
            )
            specialized_agent = self.research_agent

        # Create final crew with the specialized task
        return Crew(
            agents=[specialized_agent.create()],
            tasks=[specialized_task],
            process=Process.sequential,
            verbose=True
        )

    def _format_history(self, history: list) -> str:
        """Format conversation history for context."""
        if not history:
            return "No previous conversation context."
        
        formatted = "Previous messages:\n"
        for msg in history[-3:]:  # Last 3 messages
            formatted += f"- {msg['type']}: {msg['text']}\n"
        return formatted
