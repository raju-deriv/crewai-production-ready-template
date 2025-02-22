import pytest
import asyncio
from slack_bolt.async_app import AsyncApp
from config.settings import Settings
from main import handle_mention

@pytest.fixture
def slack_app() -> AsyncApp:
    settings = Settings()
    return AsyncApp(token=settings.slack_bot_token)

@pytest.mark.asyncio
async def test_slack_mention_handler(slack_app: AsyncApp) -> None:
    # Define a mock say function
    async def mock_say(*args, **kwargs) -> dict[str, bool]:
        return {"ok": True}

    # Simulate a Slack event
    event: dict[str, str] = {
        "text": "<@bot> research AI trends",
        "ts": "1234567890.123456"
    }
    
    # Call the handler with the mock say function
    response = await handle_mention(event, mock_say)
    assert response is None  # No exception means success