import os
from dotenv import load_dotenv

load_dotenv()

# Python 3.12+ type alias
type OptionalStr = str | None

class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.slack_bot_token: str = self._get_required("SLACK_BOT_TOKEN")
        self.slack_app_token: str = self._get_required("SLACK_APP_TOKEN")

        self.openai_api_key: str = self._get_required("OPENAI_API_KEY")
        self.openai_model: str = self._get_required("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_api_base: OptionalStr = os.getenv("OPENAI_API_BASE")

        self.anthropic_api_key: str = self._get_required("ANTHROPIC_API_KEY")
        self.anthropic_model: str = self._get_required("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.anthropic_api_base: OptionalStr = os.getenv("ANTHROPIC_API_BASE")

        # Set environment variables for CrewAI
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        print(self.openai_api_key)
        if self.openai_api_base:
            os.environ["OPENAI_API_BASE"] = self.openai_api_base
        if self.anthropic_api_base:
            os.environ["ANTHROPIC_API_BASE"] = self.anthropic_api_base

    def _get_required(self, key: str, default: OptionalStr = None) -> str:
        value = os.getenv(key, default)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value