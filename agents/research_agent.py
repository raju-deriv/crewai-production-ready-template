from crewai import Agent
from config.settings import Settings

class ResearchAgent:
    """Agent that performs research using OpenAI LLM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self) -> Agent:
        return Agent(
            role="Researcher",
            goal="Conduct thorough research on given topics",
            backstory="You're a skilled researcher with expertise in finding reliable information.",
            verbose=False,
            allow_delegation=False,
            max_iter=10,
            llm="openai/" + self.settings.openai_model
        )