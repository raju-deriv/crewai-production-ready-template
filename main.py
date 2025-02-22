from src.slack.app import SlackApp
from src.config.settings import Settings
from src.crew.research_writing_crew import ResearchWritingCrew  # Updated import
from src.utils.logging import configure_logging  # Updated import

def main() -> None:
    """Entry point for the Slack bot application."""
    configure_logging()
    settings = Settings()
    crew = ResearchWritingCrew(settings)
    slack_app = SlackApp(settings, crew)
    slack_app.start()

if __name__ == "__main__":
    main()