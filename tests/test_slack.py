import pytest
from unittest.mock import Mock, patch
from src.config.settings import Settings
from src.slack.app import SlackApp
from src.crew.research_writing_crew import ResearchWritingCrew
from typing import Dict

@pytest.fixture
def settings() -> Settings:
    """Fixture for Settings instance."""
    return Settings()

@pytest.fixture
def mock_crew(settings: Settings) -> ResearchWritingCrew:
    """Fixture for a mock ResearchWritingCrew."""
    crew = ResearchWritingCrew(settings)
    crew.run = Mock(return_value="**Test** message\n- item1\n- item2")
    return crew

@pytest.fixture
def slack_app(settings: Settings, mock_crew: ResearchWritingCrew) -> SlackApp:
    """Fixture for SlackApp instance with mocked crew."""
    return SlackApp(settings, mock_crew)

def test_handle_message_directed_to_bot(slack_app: SlackApp, mock_crew: ResearchWritingCrew) -> None:
    """Test message handling when directed to bot."""
    event = {
        "channel": "C123",
        "ts": "1234567890.123456",
        "text": "<@U123> research AI trends"
    }
    say_mock = Mock()
    # Mock the say function to return a response with a ts
    say_mock.return_value = {"ts": "processing_message_ts"}
    
    client_mock = Mock()
    client_mock.auth_test.return_value = {"user_id": "U123"}
    # Mock the chat_delete method
    client_mock.chat_delete = Mock()

    with patch.object(slack_app.app.client, "auth_test", return_value={"user_id": "U123"}):
        slack_app.handle_message(event=event, say=say_mock, client=client_mock)

    mock_crew.run.assert_called_once_with(inputs={"topic": "<@U123> research AI trends"})
    
    # Check that say was called at least twice (once for processing, once for response)
    assert say_mock.call_count >= 2
    
    # Check that chat_delete was called to remove the processing message
    client_mock.chat_delete.assert_called_once()
    
    # Get the actual text that was passed to say_mock in the last call (the formatted response)
    actual_text = say_mock.call_args[1]['text']
    
    # The message is being detected as a conversation message, which has simpler formatting
    # Verify it contains the original content but not the fancy formatting
    assert "*Test* message" in actual_text  # Original content is preserved
    # One of our bullet styles should be present
    assert any(f"{bullet} item" in actual_text for bullet in ["•", "◦", "◉", "○", "▪", "▫", "◆", "◇", "►", "▻"])
    # Verify it doesn't contain the research/information formatting
    assert ":zap:" not in actual_text  # No header for conversation messages
    assert "`Insights & Information`" not in actual_text  # No colored header for conversation messages
    
    assert "thread_ts" in say_mock.call_args[1]
    assert say_mock.call_args[1]["thread_ts"] == "1234567890.123456"
    assert say_mock.call_args[1]["mrkdwn"] is True

def test_handle_message_not_directed(slack_app: SlackApp, mock_crew: ResearchWritingCrew) -> None:
    """Test message handling when not directed to bot."""
    event = {
        "channel": "C123",
        "ts": "1234567890.123456",
        "text": "hello world"
    }
    say_mock = Mock()
    client_mock = Mock()
    client_mock.auth_test.return_value = {"user_id": "U123"}

    with patch.object(slack_app.app.client, "auth_test", return_value={"user_id": "U123"}):
        slack_app.handle_message(event=event, say=say_mock, client=client_mock)

    mock_crew.run.assert_not_called()
    say_mock.assert_not_called()

def test_handle_app_mention(slack_app: SlackApp, mock_crew: ResearchWritingCrew) -> None:
    """Test app_mention event handling."""
    event = {
        "ts": "1234567890.123456",
        "text": "<@U123> research AI trends",
        "channel": "C123"
    }
    say_mock = Mock()
    # Mock the say function to return a response with a ts
    say_mock.return_value = {"ts": "processing_message_ts"}
    
    client_mock = Mock()
    # Mock the chat_delete method
    client_mock.chat_delete = Mock()

    # Call the method
    slack_app.handle_app_mention(event=event, say=say_mock, client=client_mock)
    
    # Now app_mention calls process_message, so we expect similar behavior to handle_message
    mock_crew.run.assert_called_once_with(inputs={"topic": "<@U123> research AI trends"})
    
    # Check that say was called at least twice (once for processing, once for response)
    assert say_mock.call_count >= 2
    
    # Check that chat_delete was called to remove the processing message
    client_mock.chat_delete.assert_called_once()
    
    # Get the actual text that was passed to say_mock in the last call (the formatted response)
    actual_text = say_mock.call_args[1]['text']
    
    # The message is being detected as a conversation message, which has simpler formatting
    # Verify it contains the original content but not the fancy formatting
    assert "*Test* message" in actual_text  # Original content is preserved
    # One of our bullet styles should be present
    assert any(f"{bullet} item" in actual_text for bullet in ["•", "◦", "◉", "○", "▪", "▫", "◆", "◇", "►", "▻"])
    # Verify it doesn't contain the research/information formatting
    assert ":zap:" not in actual_text  # No header for conversation messages
    assert "`Insights & Information`" not in actual_text  # No colored header for conversation messages
    
    assert "thread_ts" in say_mock.call_args[1]
    assert say_mock.call_args[1]["thread_ts"] == "1234567890.123456"
    assert say_mock.call_args[1]["mrkdwn"] is True

def test_slack_formatting() -> None:
    """Test Slack message formatting."""
    from src.utils.formatting import format_slack_message
    
    # Test basic formatting
    input_text = "**Test** message\n- item1\n- item2"
    formatted = format_slack_message(input_text)
    
    # Check that the formatting includes our enhancements
    assert ":zap: `Insights & Information` :bulb:" in formatted  # Header with emoji and color
    assert ">" in formatted  # Block quotes for color
    # One of our bullet styles should be present
    assert any(f"{bullet} item" in formatted for bullet in ["•", "◦", "◉", "○", "▪", "▫", "◆", "◇", "►", "▻"])
    assert "_Questions? Clarifications? Just ask!_" in formatted  # Footer is present
    
    # Test weather formatting
    weather_text = "Temperature: 25°C\nHumidity: 60%\nWind Speed: 10 km/h"
    weather_formatted = format_slack_message(weather_text, message_type="weather")
    
    # Check weather-specific formatting
    assert ":thermometer:" in weather_formatted
    assert ":droplet:" in weather_formatted
    assert ":dash:" in weather_formatted
    assert "`25°C`" in weather_formatted  # Monospaced values
    
    # Test conversation formatting
    conversation_text = "Hello! How can I help you today?"
    conversation_formatted = format_slack_message(conversation_text, message_type="conversation")
    
    # Check that conversation formatting is simpler
    assert ":zap: `Insights & Information` :bulb:" not in conversation_formatted  # No header
    assert "_Questions? Clarifications? Just ask!_" not in conversation_formatted  # No footer
    assert "Hello! How can I help you today?" in conversation_formatted  # Original text is preserved
