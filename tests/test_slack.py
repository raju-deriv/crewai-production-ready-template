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
    client_mock = Mock()
    client_mock.auth_test.return_value = {"user_id": "U123"}

    with patch.object(slack_app.app.client, "auth_test", return_value={"user_id": "U123"}):
        slack_app.handle_message(event=event, say=say_mock, client=client_mock)

    mock_crew.run.assert_called_once_with(inputs={"topic": "<@U123> research AI trends"})
    
    # Check that say was called with the formatted message
    say_mock.assert_called_once()
    
    # Get the actual text that was passed to say_mock
    actual_text = say_mock.call_args[1]['text']
    
    # Verify it contains our formatting elements
    assert ":zap:" in actual_text  # New header
    assert "`Insights & Information`" in actual_text  # Colored header
    # One of our bullet styles should be present
    assert any(f"{bullet} item" in actual_text for bullet in ["•", "◦", "◉", "○", "▪", "▫", "◆", "◇", "►", "▻"])
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

    # Call the method
    slack_app.handle_app_mention(event=event, say=say_mock)
    
    # The current implementation only logs the event and doesn't process it
    # So we don't expect any calls to mock_crew.run or say_mock
    # This test just verifies that the method doesn't throw an exception
    
    # If we want to test actual functionality, we would need to implement
    # message processing in the handle_app_mention method
    mock_crew.run.assert_not_called()
    say_mock.assert_not_called()

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
    weather_formatted = format_slack_message(weather_text)
    
    # Check weather-specific formatting
    assert ":thermometer:" in weather_formatted
    assert ":droplet:" in weather_formatted
    assert ":dash:" in weather_formatted
    assert "`25°C`" in weather_formatted  # Monospaced values
