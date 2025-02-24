from src.slack.app import SlackApp
from src.config.settings import Settings
from src.crew.research_writing_crew import ResearchWritingCrew  # Updated import
from src.utils.logging import configure_logging  # Updated import

import sys
import structlog

logger = structlog.get_logger(__name__)

def main() -> None:
    """Entry point for the Slack bot application."""
    try:
        # Configure logging first
        configure_logging()
        logger.info("Starting CrewAI agent service")
        
        # Load and validate settings
        try:
            settings = Settings()
            logger.info("Settings loaded successfully", 
                       openai_model=settings.openai_model,
                       anthropic_model=settings.anthropic_model)
        except ValueError as e:
            logger.error("Failed to load settings", error=str(e))
            sys.exit(1)
        
        # Initialize crew
        try:
            crew = ResearchWritingCrew(settings)
            logger.info("Crew initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize crew", error=str(e), exc_info=True)
            sys.exit(1)
        
        # Initialize and start Slack app
        try:
            slack_app = SlackApp(settings, crew)
            logger.info("Slack app initialized successfully")
            slack_app.start()
        except Exception as e:
            logger.error("Failed to start Slack app", error=str(e), exc_info=True)
            sys.exit(1)
            
    except Exception as e:
        logger.error("Unexpected error in main application", error=str(e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
