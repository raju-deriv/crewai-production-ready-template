from crewai import Agent
import structlog
from src.config.settings import Settings
from src.tools.feedback_tool import FeedbackTool

logger = structlog.get_logger(__name__)

class FeedbackAgent:
    """Agent specialized in collecting feedback and saving it to Google Sheets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.feedback_tool = FeedbackTool(settings=settings)

    def create(self) -> Agent:
        return Agent(
            role="Feedback Collector",
            goal="Collect detailed feedback from users through structured questions and save it to Google Sheets",
            backstory="""You are a skilled feedback collector who knows how to ask the right 
            questions to gather valuable insights. You're friendly, conversational, and can adapt 
            your questioning based on previous responses. You're excellent at guiding users through 
            a feedback process while keeping them engaged. You never mention that you are an AI or 
            a conversational agent - you respond directly to users as a human agent would.""",
            verbose=False,
            allow_delegation=False,
            max_iter=5,  # Allow more iterations for multi-turn feedback collection
            llm=f"openai/{self.settings.openai_model}",
            tools=[self.feedback_tool()]  # Call the tool to get a LangChain Tool instance
        )
