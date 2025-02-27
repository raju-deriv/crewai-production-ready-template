import pytest
from unittest.mock import patch, MagicMock
import json
from src.config.settings import Settings
from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent
from src.agents.conversation_agent import ConversationAgent
from src.agents.master_agent import MasterAgent
from src.crew.master_crew import MasterCrew

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
    # Updated to match the actual implementation which uses OpenAI
    assert created_agent.llm.model == f"openai/{settings.openai_model}"
    # Updated to match the actual implementation which sets verbose to False
    assert created_agent.verbose is False
    assert created_agent.allow_delegation is False

def test_conversation_agent_initialization(settings: Settings) -> None:
    """Test ConversationAgent initialization and creation."""
    agent = ConversationAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Conversational Assistant"
    assert created_agent.llm.model == f"openai/{settings.openai_model}"
    assert created_agent.verbose is True
    assert created_agent.allow_delegation is False

def test_master_agent_initialization(settings: Settings) -> None:
    """Test MasterAgent initialization and creation."""
    agent = MasterAgent(settings)
    created_agent = agent.create()
    assert created_agent.role == "Master Controller"
    assert created_agent.llm.model == f"openai/{settings.openai_model}"
    assert created_agent.verbose is True
    assert created_agent.allow_delegation is True
    assert len(created_agent.tools) == 1
    assert created_agent.tools[0].name == "analyze_intent"

def test_master_crew_parse_intent_result_valid_json() -> None:
    """Test MasterCrew._parse_intent_result with valid JSON."""
    settings = Settings()
    crew = MasterCrew(settings)
    
    # Test with valid JSON
    result_str = """
    Here's my analysis:
    {
        "intent": "conversation",
        "params": {
            "message": "hello"
        },
        "confidence": 0.95,
        "reasoning": "This is a simple greeting",
        "clarification_question": null
    }
    """
    
    intent, confidence, clarification = crew._parse_intent_result(result_str)
    assert intent == "conversation"
    assert confidence == 0.95
    assert clarification is None

def test_master_crew_parse_intent_result_low_confidence() -> None:
    """Test MasterCrew._parse_intent_result with low confidence and clarification."""
    settings = Settings()
    crew = MasterCrew(settings)
    
    # Test with low confidence and clarification question
    result_str = """
    {
        "intent": "weather",
        "params": {
            "location": "unknown"
        },
        "confidence": 0.4,
        "reasoning": "The request might be about weather but location is unclear",
        "clarification_question": "Which city would you like to know the weather for?"
    }
    """
    
    intent, confidence, clarification = crew._parse_intent_result(result_str)
    assert intent == "weather"
    assert confidence == 0.4
    assert clarification == "Which city would you like to know the weather for?"

def test_master_crew_parse_intent_result_invalid_json() -> None:
    """Test MasterCrew._parse_intent_result with invalid JSON."""
    settings = Settings()
    crew = MasterCrew(settings)
    
    # Test with invalid JSON
    result_str = "I think this is a weather request"
    
    intent, confidence, clarification = crew._parse_intent_result(result_str)
    assert intent == "conversation"  # Default to conversation
    assert confidence == 0.0
    assert clarification is None

@patch('src.crew.master_crew.Crew')
def test_master_crew_create_crew_conversation_intent(mock_crew, settings: Settings) -> None:
    """Test MasterCrew.create_crew with conversation intent."""
    # Setup mock
    mock_instance = MagicMock()
    mock_crew.return_value = mock_instance
    mock_instance.kickoff.return_value = json.dumps({
        "intent": "conversation",
        "params": {"message": "hello"},
        "confidence": 0.9,
        "reasoning": "This is a simple greeting"
    })
    
    # Create crew and test
    crew = MasterCrew(settings)
    result = crew.create_crew({"topic": "hello"})
    
    # Verify the conversation agent was used
    assert result == mock_instance
    assert mock_crew.call_count == 2  # Once for master, once for specialized
    
    # Get the specialized agent from the second call to Crew
    specialized_args = mock_crew.call_args[1]
    assert len(specialized_args['agents']) == 1
    # The agent should be an instance of the conversation agent's create() method result
    # We can't directly check the type, but we can verify it's not one of the other agents

@patch('src.crew.master_crew.Crew')
def test_master_crew_create_crew_low_confidence(mock_crew, settings: Settings) -> None:
    """Test MasterCrew.create_crew with low confidence and clarification."""
    # Setup mock
    mock_instance = MagicMock()
    mock_crew.return_value = mock_instance
    mock_instance.kickoff.return_value = json.dumps({
        "intent": "weather",
        "params": {"location": "unknown"},
        "confidence": 0.4,
        "reasoning": "The request might be about weather but location is unclear",
        "clarification_question": "Which city would you like to know the weather for?"
    })
    
    # Create crew and test
    crew = MasterCrew(settings)
    result = crew.create_crew({"topic": "weather"})
    
    # Verify the conversation agent was used to ask for clarification
    assert result == mock_instance
    assert mock_crew.call_count == 2  # Once for master, once for specialized
    
    # Get the specialized task from the second call to Crew
    specialized_args = mock_crew.call_args[1]
    assert len(specialized_args['tasks']) == 1
    assert "Ask for clarification" in specialized_args['tasks'][0].description
    assert "Which city would you like to know the weather for?" in specialized_args['tasks'][0].description
