from src.slack.app import SlackApp
from src.config.settings import Settings
from src.crew.master_crew import MasterCrew
from src.utils.logging import configure_logging
from src.auth.role_manager import RoleManager
from src.storage.approval_store import ApprovalStore

import sys
import structlog

logger = structlog.get_logger(__name__)

def main() -> None:
    """Entry point for the CrewAI agent service."""
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
        
        # Initialize role manager and approval store
        try:
            role_manager = RoleManager(settings)
            logger.info("Role manager initialized successfully")
            
            approval_store = ApprovalStore(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                ssl=settings.redis_ssl,
                ttl=settings.redis_ttl
            )
            logger.info("Approval store initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize role manager or approval store", error=str(e), exc_info=True)
            sys.exit(1)
        
        # Initialize master crew with role manager and approval store
        try:
            crew = MasterCrew(settings, role_manager=role_manager, approval_store=approval_store)
            logger.info("Master crew initialized successfully with role-based access control")
        except Exception as e:
            logger.error("Failed to initialize master crew", error=str(e), exc_info=True)
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
