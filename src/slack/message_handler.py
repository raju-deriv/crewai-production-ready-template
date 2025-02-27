from typing import Any, Dict, List
from datetime import datetime
import structlog
from src.crew.base_crew import BaseCrew
from src.utils.formatting import format_slack_message
from src.storage.redis_client import RedisConversationStore, RedisConnectionError

logger = structlog.get_logger(__name__)

class MessageHandler:
    """Handles Slack message processing and responses."""

    def __init__(self, crew: BaseCrew, conversation_store: RedisConversationStore):
        self.crew = crew
        self.conversation_store = conversation_store
        self.logger = structlog.get_logger(__name__)

    def process_message(self, text: str, say: Any, thread_ts: str, channel_id: str, client: Any = None) -> None:
        """Process incoming messages and handle responses."""
        try:
            # Store incoming message
            message_data = {
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "type": "incoming"
            }
            self.conversation_store.store_message(channel_id, thread_ts, message_data)
            self.logger.debug("Stored incoming message", message_data=message_data)

            # Send an initial "processing" message
            processing_message = ":hourglass_flowing_sand: `Processing your request...` :writing_hand:"
            processing_response = say(
                text=processing_message,
                thread_ts=thread_ts,
                mrkdwn=True
            )
            
            # Get the timestamp of the processing message so we can delete it later
            processing_ts = processing_response.get('ts')
            
            # Get conversation history for context
            history = self.get_conversation_history(channel_id, thread_ts)
            
            # Run the crew task with conversation history
            inputs = {
                "topic": text,
                "conversation_history": history
            }
            response = self.crew.run(inputs=inputs)
            
            # Delete the processing message if we have its timestamp
            if processing_ts and client:
                try:
                    # Use the client to delete the message
                    client.chat_delete(
                        channel=channel_id,
                        ts=processing_ts
                    )
                    self.logger.debug("Deleted processing message", ts=processing_ts)
                except Exception as e:
                    self.logger.error("Failed to delete processing message", error=str(e), exc_info=True)
            
            # Send the actual response
            self._send_response(response, say, thread_ts, channel_id)

        except RedisConnectionError as e:
            self.logger.error("Redis connection error", error=str(e))
            # Send an initial "processing" message
            processing_message = ":hourglass_flowing_sand: `Processing your request...` :writing_hand:"
            processing_response = say(
                text=processing_message,
                thread_ts=thread_ts,
                mrkdwn=True
            )
            
            # Get the timestamp of the processing message so we can delete it later
            processing_ts = processing_response.get('ts')
            
            # Continue processing even if Redis fails
            response = self.crew.run(inputs={"topic": text})
            
            # Delete the processing message if we have its timestamp
            if processing_ts and client:
                try:
                    # Use the client to delete the message
                    client.chat_delete(
                        channel=channel_id,
                        ts=processing_ts
                    )
                    self.logger.debug("Deleted processing message", ts=processing_ts)
                except Exception as e:
                    self.logger.error("Failed to delete processing message", error=str(e), exc_info=True)
            
            self._send_response(response, say, thread_ts, channel_id, store_history=False)

        except Exception as e:
            self.logger.error("Error processing message", error=str(e), exc_info=True)
            error_message = format_slack_message(f"Sorry, I encountered an error: {str(e)}", bold=True)
            say(text=error_message, thread_ts=thread_ts, mrkdwn=True)

    def _send_response(self, response: str, say: Any, thread_ts: str, 
                      channel_id: str, store_history: bool = True) -> None:
        """Send formatted response message and store in history."""
        # Detect if this is likely a conversation response
        message_type = self._detect_message_type(response)
        
        formatted_response = format_slack_message(
            response, 
            message_type=message_type
        ) if response else "*Processing your request...*"
        
        self.logger.debug("Sending formatted response", 
                         response=formatted_response,
                         message_type=message_type,
                         thread_ts=thread_ts)

        say(
            text=formatted_response,
            thread_ts=thread_ts,
            mrkdwn=True
        )
        
        if store_history:
            try:
                message_data = {
                    "text": formatted_response,
                    "timestamp": datetime.now().isoformat(),
                    "type": "outgoing"
                }
                self.conversation_store.store_message(channel_id, thread_ts, message_data)
                self.logger.debug("Stored outgoing message", message_data=message_data)
            except RedisConnectionError as e:
                self.logger.error("Failed to store response in history", error=str(e))
    
    def _detect_message_type(self, response: str) -> str:
        """
        Detect the type of message based on content heuristics.
        
        Args:
            response: The response text
            
        Returns:
            The detected message type ('conversation', 'weather', 'research', etc.)
        """
        # Convert to lowercase for case-insensitive matching
        lower_response = response.lower()
        
        # Check for conversation patterns
        conversation_patterns = [
            # Greetings
            "hello", "hi there", "hey", "greetings", 
            # Simple responses
            "you're welcome", "thank you", "thanks for", 
            # Clarification questions
            "could you please clarify", "i'm not sure what you mean",
            "can you provide more details", "would you like me to",
            # Short responses (less than 100 characters are likely conversational)
            # But only if they don't contain weather or research indicators
            # This should be checked last
        ]
        
        # Check for weather patterns
        weather_patterns = [
            "temperature", "humidity", "wind speed", "precipitation",
            "forecast", "weather", "sunny", "cloudy", "rainy", "celsius", 
            "fahrenheit", "degrees", "climate", "atmospheric"
        ]
        
        # Check for research patterns
        research_patterns = [
            "according to", "research shows", "studies indicate",
            "analysis", "findings", "data suggests", "evidence",
            "conclusion", "summary", "in conclusion"
        ]
        
        # Check for patterns in order of specificity
        if any(pattern in lower_response for pattern in weather_patterns):
            return "weather"
        elif any(pattern in lower_response for pattern in research_patterns):
            return "research"
        elif any(pattern in lower_response for pattern in conversation_patterns):
            return "conversation"
        elif len(response) < 100 and not any(pattern in lower_response for pattern in weather_patterns + research_patterns):
            # Short responses without specific indicators are likely conversational
            return "conversation"
            
        # Default to a generic type if no patterns match
        return "generic"

    def get_conversation_history(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Get conversation history for a thread."""
        try:
            messages = self.conversation_store.get_messages(channel_id, thread_ts)
            # Extend TTL when conversation is accessed
            if messages:
                self.conversation_store.extend_ttl(channel_id, thread_ts)
            return messages
        except RedisConnectionError as e:
            self.logger.error("Failed to retrieve conversation history", error=str(e))
            return []
