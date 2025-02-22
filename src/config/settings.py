import os
from dotenv import load_dotenv
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Root directory
dotenv_path = BASE_DIR / ".env"
if not dotenv_path.exists():
    logger.warning(f".env file not found at {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path, verbose=True)
logger.debug(f"Loaded .env file from {dotenv_path}")

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

        # Set CrewAI environment variables
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        if self.openai_api_base:
            os.environ["OPENAI_API_BASE"] = self.openai_api_base
        if self.anthropic_api_base:
            os.environ["ANTHROPIC_API_BASE"] = self.anthropic_api_base

        logger.debug("Settings initialized", slack_bot_token=self.slack_bot_token[:4] + "...",
                     openai_model=self.openai_model)

    def _get_required(self, key: str, default: OptionalStr = None) -> str:
        value = os.getenv(key, default)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value