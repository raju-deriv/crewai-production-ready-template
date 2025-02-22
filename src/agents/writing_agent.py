from crewai import Agent
from src.config.settings import Settings

class WritingAgent:
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
            llm=f"openai/{self.settings.openai_model}"
        )