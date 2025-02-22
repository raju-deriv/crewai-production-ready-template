from typing import Any, Dict
from datetime import datetime
import structlog
from src.crew.base_crew import BaseCrew  # Updated import
from src.utils.formatting import format_slack_message  # Updated import

logger = structlog.get_logger(__name__)

class MessageHandler:
    """Handles Slack message processing and responses."""

    def __init__(self, crew: BaseCrew):
        self.crew = crew
        self.logger = structlog.get_logger(__name__)

    def process_message(self, text: str, say: Any, thread_ts: str) -> None:
        """Process incoming messages and handle responses."""
        try:
            message_data = {
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "type": "incoming"
            }
            self.logger.debug("Received message", message_data=message_data)

            # Run the crew task
            response = self.crew.run(inputs={"topic": text})
            self._send_response(response, say, thread_ts)

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_message = format_slack_message(f"Sorry, I encountered an error: {str(e)}", bold=True)
            say(text=error_message, thread_ts=thread_ts, mrkdwn=True)

    def _send_response(self, response: str, say: Any, thread_ts: str) -> None:
        """Send formatted response message and store in history."""
        formatted_response = format_slack_message(response) if response else "*Processing your request...*"
        self.logger.debug("Sending formatted response", response=formatted_response, thread_ts=thread_ts)

        say(
            text=formatted_response,
            thread_ts=thread_ts,
            mrkdwn=True
        )

        message_data = {
            "text": formatted_response,
            "timestamp": datetime.now().isoformat(),
            "type": "outgoing"
        }
        self.logger.debug("Sent response", message_data=message_data)