from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)

class ResearchInput(BaseModel):
    """Input schema for ResearchTool."""
    topic: str = Field(..., description="The topic to research")

class ResearchTool(BaseTool):
    name: str = "research_topic"
    description: str = """
    Research a given topic thoroughly and provide comprehensive information.
    Break down complex topics into understandable sections.
    Include relevant facts, explanations, and context.
    """
    args_schema: type[BaseModel] = ResearchInput

    def __init__(self):
        super().__init__()

    def _run(self, topic: str) -> str:
        """
        Research a given topic and provide comprehensive information.

        Args:
            topic: The topic to research

        Returns:
            Detailed research results as a string
        """
        prompt = f"""
        Conduct thorough research on: {topic}

        Please provide:
        1. Overview and key concepts
           - Main ideas and fundamental principles
           - Basic definitions and terminology

        2. Important details and explanations
           - In-depth analysis of key aspects
           - How different components work or relate
           - Technical details when relevant

        3. Relevant context and implications
           - Historical background if applicable
           - Current significance and applications
           - Future implications or potential developments

        4. Current developments or state of knowledge
           - Latest research or findings
           - Current trends and directions
           - Notable recent developments

        5. Important considerations or caveats
           - Limitations or challenges
           - Competing theories or viewpoints
           - Areas of uncertainty or debate

        Structure your response in a clear, organized manner.
        Use examples where appropriate to illustrate concepts.
        Include citations or references when discussing specific findings or claims.
        """
        return prompt
