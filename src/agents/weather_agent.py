from crewai import Agent
import structlog
from src.config.settings import Settings
from src.tools.weather_tool import WeatherTool

logger = structlog.get_logger(__name__)

class WeatherAgent:
    """Agent specialized in providing weather information."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.weather_tool = WeatherTool(settings)

    def create(self) -> Agent:
        return Agent(
            role="Weather Expert",
            goal="Provide accurate weather forecasts and conditions for any location",
            backstory="""You are a meteorologist with expertise in weather forecasting. 
            You have access to professional weather data and can provide detailed weather 
            information for any location.""",
            verbose=False,
            allow_delegation=False,
            max_iter=2,
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.weather_tool]
        )
