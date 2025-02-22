from crewai import Agent
from config.settings import Settings

class WritingAgent:
    """Agent that writes content using Anthropic Claude LLM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self) -> Agent:
        return Agent(
            role="Writer",
            goal="Produce clear and engaging written content",
            backstory="You're a professional writer with a knack for crafting compelling narratives.",
            verbose=False,
            allow_delegation=False,
            max_iter=10,
            llm="openai/" + self.settings.openai_model
        )