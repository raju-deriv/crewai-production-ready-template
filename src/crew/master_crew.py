from crewai import Crew, Process, Task
from typing import Dict, Any, Optional
import structlog
import json
from src.config.settings import Settings
from src.agents.master_agent import MasterAgent
from src.agents.research_agent import ResearchAgent
from src.agents.weather_agent import WeatherAgent
from src.agents.rag_query_agent import RAGQueryAgent
from src.agents.document_management_agent import DocumentManagementAgent
from src.agents.conversation_agent import ConversationAgent
from src.crew.base_crew import BaseCrew

logger = structlog.get_logger(__name__)

class MasterCrew(BaseCrew):
    """Master crew that routes requests to appropriate specialized crews."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.master_agent = MasterAgent(settings)
        self.research_agent = ResearchAgent(settings)
        self.weather_agent = WeatherAgent(settings)
        self.rag_query_agent = RAGQueryAgent(settings)
        self.document_management_agent = DocumentManagementAgent(settings)
        self.conversation_agent = ConversationAgent(settings)
        self.confidence_threshold = 0.7

    def create_crew(self, inputs: dict[str, str]) -> Crew:
        """Create a crew with the master agent and appropriate specialized agents."""
        request = inputs.get("topic", "")  # Using 'topic' for backward compatibility
        conversation_history = inputs.get("conversation_history", [])

        # Create the master agent task to analyze intent
        context_info = [
            f"User request: {request}",
            f"Previous conversation context: {self._format_history(conversation_history)}",
            "Determine which specialized agent should handle this request.",
            "Consider the full context and the specific capabilities of each agent.",
            "Return your analysis in JSON format with intent, parameters, confidence, and reasoning."
        ]
        
        master_task = Task(
            description=f"Analyze this request and determine which agent should handle it: {request}\n\n{' '.join(context_info)}",
            expected_output="JSON object with intent analysis",
            agent=self.master_agent.create()
        )

        # Create the crew with just the master task initially
        crew = Crew(
            agents=[self.master_agent.create()],
            tasks=[master_task],
            process=Process.sequential,
            verbose=True
        )

        # Get the master agent's decision
        result = crew.kickoff()
        result_str = str(result)
        logger.info("Master agent analysis", result=result_str)

        # Parse the result to extract intent, confidence, and clarification question
        intent, confidence, clarification_question = self._parse_intent_result(result_str)
        
        # If confidence is below threshold and we have a clarification question, use the conversation agent to ask it
        if confidence < self.confidence_threshold and clarification_question:
            logger.info("Low confidence intent detection", 
                       intent=intent, 
                       confidence=confidence, 
                       clarification_question=clarification_question)
            
            clarification_context = [
                "The user's request is ambiguous or unclear.",
                f"Previous conversation: {self._format_history(conversation_history)}",
                f"Original request: {request}",
                f"Please ask this clarification question: {clarification_question}"
            ]
            
            specialized_task = Task(
                description=f"Ask for clarification\n\n{' '.join(clarification_context)}",
                expected_output="A polite response asking for clarification without mentioning that you are an AI or conversational agent",
                agent=self.conversation_agent.create()
            )
            specialized_agent = self.conversation_agent
        else:
            # Route to the appropriate specialized agent based on intent
            if intent == "weather":
                weather_context = [
                    "The user wants weather information.",
                    f"Previous conversation: {self._format_history(conversation_history)}",
                    f"Original request: {request}"
                ]
                
                specialized_task = Task(
                    description=f"Get weather information\n\n{' '.join(weather_context)}",
                    expected_output="Weather information for the requested location",
                    agent=self.weather_agent.create()
                )
                specialized_agent = self.weather_agent
            elif intent == "rag_query":
                rag_context = [
                    "The user wants to query the knowledge base.",
                    f"Previous conversation: {self._format_history(conversation_history)}",
                    f"Original request: {request}"
                ]
                
                specialized_task = Task(
                    description=f"Query the knowledge base\n\n{' '.join(rag_context)}",
                    expected_output="Information retrieved from the knowledge base",
                    agent=self.rag_query_agent.create()
                )
                specialized_agent = self.rag_query_agent
            elif intent == "doc_management":
                doc_context = [
                    "The user wants to manage documents in the knowledge base.",
                    f"Previous conversation: {self._format_history(conversation_history)}",
                    f"Original request: {request}"
                ]
                
                specialized_task = Task(
                    description=f"Manage documents in the knowledge base\n\n{' '.join(doc_context)}",
                    expected_output="Confirmation of document management operation",
                    agent=self.document_management_agent.create()
                )
                specialized_agent = self.document_management_agent
            elif intent == "conversation":
                conversation_context = [
                    "The user is engaging in general conversation.",
                    f"Previous conversation: {self._format_history(conversation_history)}",
                    f"Original request: {request}"
                ]
                
                specialized_task = Task(
                    description=f"Engage in conversation\n\n{' '.join(conversation_context)}",
                    expected_output="A friendly and helpful response that directly addresses the user's query without mentioning that you are an AI or conversational agent",
                    agent=self.conversation_agent.create()
                )
                specialized_agent = self.conversation_agent
            else:  # Default to research for any other intent
                research_context = [
                    "The user wants information about a topic.",
                    f"Previous conversation: {self._format_history(conversation_history)}",
                    f"Original request: {request}"
                ]
                
                specialized_task = Task(
                    description=f"Research the topic\n\n{' '.join(research_context)}",
                    expected_output="Detailed research information about the requested topic",
                    agent=self.research_agent.create()
                )
                specialized_agent = self.research_agent

        # Create final crew with the specialized task
        return Crew(
            agents=[specialized_agent.create()],
            tasks=[specialized_task],
            process=Process.sequential,
            verbose=True
        )

    def _parse_intent_result(self, result_str: str) -> tuple[str, float, Optional[str]]:
        """
        Parse the intent analysis result to extract intent, confidence, and clarification question.
        
        Args:
            result_str: The string representation of the intent analysis result
            
        Returns:
            A tuple of (intent, confidence, clarification_question)
        """
        # Default values
        intent = "conversation"  # Default to conversation if parsing fails
        confidence = 0.0
        clarification_question = None
        
        try:
            # Try to extract JSON from the result string
            # First, find the start of the JSON object
            json_start = result_str.find("{")
            if json_start >= 0:
                # Extract the JSON part of the string
                json_str = result_str[json_start:]
                # Parse the JSON
                result_json = json.loads(json_str)
                
                # Extract the values
                intent = result_json.get("intent", "conversation").lower()
                confidence = float(result_json.get("confidence", 0.0))
                clarification_question = result_json.get("clarification_question")
                
                logger.debug("Parsed intent result", 
                           intent=intent, 
                           confidence=confidence, 
                           clarification_question=clarification_question)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse intent result", error=str(e), result=result_str)
            # If we can't parse the JSON, use simple string matching as fallback
            intent_mapping = {
                "weather": "weather",
                "rag_query": "rag_query",
                "doc_management": "doc_management",
                "research": "research",
                "conversation": "conversation"
            }
            
            for key, value in intent_mapping.items():
                if key in result_str.lower():
                    intent = value
                    break
        
        return intent, confidence, clarification_question

    def _format_history(self, history: list) -> str:
        """Format conversation history for context."""
        if not history:
            return "No previous conversation context."
        
        formatted = "Previous messages:\n"
        for msg in history[-3:]:  # Last 3 messages
            formatted += f"- {msg['type']}: {msg['text']}\n"
        return formatted
