from crewai import Agent
from typing import Dict, Any
import structlog
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class ConversationAgent:
    """Conversational agent that handles general conversation and ambiguous requests."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self) -> Agent:
        return Agent(
            role="Conversational Assistant",
            goal="Engage in natural conversation and help clarify user intentions when requests are ambiguous",
            backstory="""You are a friendly and helpful assistant. You excel at 
            engaging in natural dialogue, responding to greetings, and helping users clarify their 
            intentions when their requests are ambiguous. You're the first point of contact when 
            the system isn't sure what the user wants. Never mention that you are an AI, a model, 
            or a conversational agent - just respond directly to the user's queries as a human agent would.""",
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            llm=f"openai/{self.settings.openai_model}"
        )
