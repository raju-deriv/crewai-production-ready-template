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
    Return a structured analysis with intent, parameters, confidence, and reasoning.
    If the intent is unclear or the confidence is low, suggest a clarification question.
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

        3. RAG Query Agent
           - Retrieves information from the knowledge base
           - Good for specific questions about documents in the system
           - Examples: "What do our documents say about project X?", "Find information about Y in our knowledge base"

        4. Document Management Agent
           - Handles document ingestion and management
           - Good for adding, updating, or removing documents
           - Examples: "Add this PDF to the knowledge base", "Index this website", "Remove document X"

        5. Conversation Agent
           - Handles general conversation, greetings, and ambiguous requests
           - Good for casual interactions and clarifying user intentions
           - Examples: "Hello", "How are you?", "Thanks", "I'm not sure what I need"

        Analyze the request and determine:
        1. Which agent is best suited to handle this request
        2. What specific parameters they need
        3. How confident you are in this decision (use a low confidence score for ambiguous requests)
        4. Your reasoning for this choice
        5. If confidence is below 0.7, suggest a clarification question to ask the user

        IMPORTANT: For simple greetings, casual conversation, or ambiguous requests, assign to the Conversation Agent with appropriate confidence.
        DO NOT default to the Weather Agent for ambiguous requests or simple greetings.
        
        Return your analysis in this exact JSON format:
        {{
            "intent": "research, weather, rag_query, doc_management, or conversation",
            "params": {{
                "topic" or "location" or "query" or "document_source" or "message": "extracted parameter",
                "document_type": "optional document type for doc_management"
            }},
            "confidence": 0.0 to 1.0,
            "reasoning": "Brief explanation of your decision",
            "clarification_question": "Question to ask if confidence < 0.7, otherwise null"
        }}
        """
        return prompt
