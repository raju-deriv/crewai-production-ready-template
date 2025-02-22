import pytest
from src.config.settings import Settings
from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent

@pytest.fixture
def settings() -> Settings:
    """Fixture for Settings instance."""
    return Settings()

def test_research_agent_initialization(settings: Settings) -> None:
    """Test ResearchAgent initialization and creation."""
    agent = ResearchAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Researcher"
    assert created_agent.llm.model == f"openai/{settings.openai_model}"
    assert created_agent.verbose is True
    assert created_agent.allow_delegation is False

def test_writing_agent_initialization(settings: Settings) -> None:
    """Test WritingAgent initialization and creation."""
    agent = WritingAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Writer"
    assert created_agent.llm.model == f"anthropic/{settings.anthropic_model}"
    assert created_agent.verbose is True
    assert created_agent.allow_delegation is False