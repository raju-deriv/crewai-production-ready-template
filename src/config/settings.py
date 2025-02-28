import os
from dotenv import load_dotenv
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)

class EnvironmentError(Exception):
    """Custom exception for environment-related errors."""
    pass

class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self._load_environment()
        self._validate_and_set_variables()
        self._configure_crewai_environment()
        self._configure_redis()
        self._configure_rag()
        self._log_initialization()

    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        dotenv_path = BASE_DIR / ".env"
        
        if not dotenv_path.exists():
            logger.warning("Environment setup", status="warning", 
                         message=f".env file not found at {dotenv_path}")
        
        load_dotenv(dotenv_path=dotenv_path, verbose=True)
        logger.debug("Environment setup", status="success",
                    message=f"Attempted to load .env from {dotenv_path}")

    def _validate_and_set_variables(self) -> None:
        """Validate and set all required environment variables."""
        try:
            # Required variables with validation
            self.slack_bot_token = self._validate_token(
                self._get_required("SLACK_BOT_TOKEN"), "xoxb-")
            self.slack_app_token = self._validate_token(
                self._get_required("SLACK_APP_TOKEN"), "xapp-")
            self.openai_api_key = self._validate_token(
                self._get_required("OPENAI_API_KEY"), "sk-")
            self.anthropic_api_key = self._get_required("ANTHROPIC_API_KEY")

            # Variables with defaults
            self.openai_model = self._get_required(
                "OPENAI_MODEL", "gpt-4o-mini")
            self.anthropic_model = self._get_required(
                "ANTHROPIC_MODEL", "claude-3-haiku-20240307")

            # Optional variables
            self.openai_api_base = os.getenv("OPENAI_API_BASE")
            self.anthropic_api_base = os.getenv("ANTHROPIC_API_BASE")
            
            # Role-based access control
            admin_ids = os.getenv("ADMIN_USER_IDS", "")
            self.admin_user_ids = [uid.strip() for uid in admin_ids.split(",") if uid.strip()]

            # Redis configuration
            self.redis_host = self._get_required("REDIS_HOST", "redis")
            self.redis_port = int(self._get_required("REDIS_PORT", "6379"))
            self.redis_password = os.getenv("REDIS_PASSWORD")
            self.redis_db = int(self._get_required("REDIS_DB", "0"))
            self.redis_ssl = self._get_required("REDIS_SSL", "true").lower() == "true"
            self.redis_ttl = int(self._get_required("REDIS_TTL", "86400"))

            # Weather API configuration (using WeatherAPI.com instead of OpenWeather)
            self.openweather_api_key = self._get_required("OPENWEATHER_API_KEY")
            # Note: We're still using the OPENWEATHER_API_KEY env variable name for backward compatibility
            # but it should now contain a WeatherAPI.com API key

        except ValueError as e:
            raise EnvironmentError(f"Environment validation failed: {str(e)}")

    def _configure_redis(self) -> None:
        """Configure Redis-specific settings."""
        logger.info(
            "Redis configuration",
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            ssl=self.redis_ssl,
            ttl=self.redis_ttl
        )

    def _configure_crewai_environment(self) -> None:
        """Configure CrewAI-specific environment variables."""
        # Set API bases first to ensure they're configured before any API client initialization
        if self.openai_api_base:
            os.environ["OPENAI_API_BASE"] = self.openai_api_base
            logger.info("Set custom OpenAI API base", base_url=self.openai_api_base)
        if self.anthropic_api_base:
            os.environ["ANTHROPIC_API_BASE"] = self.anthropic_api_base
            logger.info("Set custom Anthropic API base", base_url=self.anthropic_api_base)

        # Set API keys after bases are configured
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key

        # Set additional OpenAI configurations
        os.environ["OPENAI_API_TYPE"] = "open_ai"
        if self.openai_api_base and "azure" in self.openai_api_base.lower():
            os.environ["OPENAI_API_TYPE"] = "azure"

    def _configure_rag(self) -> None:
        """Configure RAG-specific settings."""
        # Vector Database Configuration
        self.vector_db_provider = os.getenv("VECTOR_DB_PROVIDER", "pinecone")
        
        # Pinecone Configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
        self.pinecone_index = os.getenv("PINECONE_INDEX", "documents")
        
        # Chroma Configuration
        self.chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.chroma_collection = os.getenv("CHROMA_COLLECTION", "documents")
        
        # Embedding Configuration
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
        self.openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.st_model = os.getenv("ST_MODEL", "all-MiniLM-L6-v2")
        
        # Document Processing Configuration
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.cache_dir = os.getenv("CACHE_DIR", "./document_cache")
        
        # External Services Configuration
        self.google_credentials = os.getenv("GOOGLE_CREDENTIALS")
        self.dropbox_app_key = os.getenv("DROPBOX_APP_KEY")
        self.dropbox_app_secret = os.getenv("DROPBOX_APP_SECRET")
        self.dropbox_refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
        
        # Feedback Agent Configuration
        self.google_sheets_credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
        self.google_service_account_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        self.feedback_spreadsheet_id = os.getenv("FEEDBACK_SPREADSHEET_ID")
        
        logger.info(
            "RAG configuration initialized",
            vector_db_provider=self.vector_db_provider,
            embedding_provider=self.embedding_provider,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            cache_enabled=self.cache_enabled
        )

    def _log_initialization(self) -> None:
        """Log initialization status and configuration."""
        logger.info(
            "Settings initialized",
            slack_bot_token_prefix=self.slack_bot_token[:8] + "...",
            slack_app_token_prefix=self.slack_app_token[:8] + "...",
            openai_model=self.openai_model,
            anthropic_model=self.anthropic_model,
            openai_api_base=self.openai_api_base or "default",
            anthropic_api_base=self.anthropic_api_base or "default"
        )

    def _get_required(self, key: str, default: Optional[str] = None) -> str:
        """Get a required environment variable."""
        value = os.getenv(key, default)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    def _validate_token(self, token: str, expected_prefix: str) -> str:
        """Validate token format."""
        if not token.startswith(expected_prefix):
            raise ValueError(
                f"Invalid token format. Expected prefix '{expected_prefix}' for token: {token[:4]}...")
        return token
