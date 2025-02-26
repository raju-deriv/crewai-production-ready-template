from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class IntentAnalyzerInput(BaseModel):
    """Input schema for IntentAnalyzerTool."""
    request: str = Field(..., description="The user's request text to analyze")
    conversation_history: Optional[str] = Field(None, description="Optional conversation history for context")

class IntentAnalyzerTool(BaseTool):
    name: str = "analyze_intent"
    description: str = """
    Analyze the user's request to determine which specialized agent should handle it.
    Consider the full context including any conversation history.
    Return a structured analysis with intent, parameters, and reasoning.
    """
    args_schema: type[BaseModel] = IntentAnalyzerInput

    def __init__(self):
        super().__init__()

    def _run(self, request: str, conversation_history: Optional[str] = None) -> str:
        """
        Analyze the user's request to determine which agent should handle it.

        Args:
            request: The user's request text
            conversation_history: Optional conversation history for context

        Returns:
            A prompt for the LLM to analyze the request
        """
        prompt = f"""
        Analyze this user request: "{request}"

        {conversation_history if conversation_history else "No conversation history available."}

        Available specialized agents:
        1. Research Agent
           - Handles research queries and information gathering
           - Good for questions about topics, concepts, or general information
           - Examples: "Tell me about quantum computing", "Research renewable energy"

        2. Weather Agent
           - Provides weather forecasts and conditions
           - Handles location-specific weather queries
           - Examples: "Weather in London", "Will it rain tomorrow in Paris"

        Analyze the request and determine:
        1. Which agent is best suited to handle this request
        2. What specific parameters they need
        3. How confident you are in this decision
        4. Your reasoning for this choice

        Return your analysis in this exact JSON format:
        {{
            "intent": "research or weather",
            "params": {{
                "topic" or "location": "extracted parameter"
            }},
            "confidence": 0.0 to 1.0,
            "reasoning": "Brief explanation of your decision"
        }}
        """
        return prompt
