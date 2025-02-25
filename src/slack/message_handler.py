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

    def process_message(self, text: str, say: Any, thread_ts: str, channel_id: str) -> None:
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

            # Get conversation history for context
            history = self.get_conversation_history(channel_id, thread_ts)
            
            # Run the crew task with conversation history
            inputs = {
                "topic": text,
                "conversation_history": history
            }
            response = self.crew.run(inputs=inputs)
            self._send_response(response, say, thread_ts, channel_id)

        except RedisConnectionError as e:
            self.logger.error("Redis connection error", error=str(e))
            # Continue processing even if Redis fails
            response = self.crew.run(inputs={"topic": text})
            self._send_response(response, say, thread_ts, channel_id, store_history=False)

        except Exception as e:
            self.logger.error("Error processing message", error=str(e), exc_info=True)
            error_message = format_slack_message(f"Sorry, I encountered an error: {str(e)}", bold=True)
            say(text=error_message, thread_ts=thread_ts, mrkdwn=True)

    def _send_response(self, response: str, say: Any, thread_ts: str, 
                      channel_id: str, store_history: bool = True) -> None:
        """Send formatted response message and store in history."""
        formatted_response = format_slack_message(response) if response else "*Processing your request...*"
        self.logger.debug("Sending formatted response", 
                         response=formatted_response, 
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
