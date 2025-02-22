import pytest
from config.settings import Settings
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent

@pytest.fixture
def settings() -> Settings:
    return Settings()

def test_research_agent_initialization(settings: Settings) -> None:
    agent = ResearchAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Researcher"
    assert created_agent.llm.model == f"openai/{settings.openai_model}"  # Check LLM object's model attribute

def test_writing_agent_initialization(settings: Settings) -> None:
    agent = WritingAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Writer"
    assert created_agent.llm.model == f"anthropic/{settings.anthropic_model}"  # Check LLM object's model attribute