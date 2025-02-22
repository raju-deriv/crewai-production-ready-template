from typing import Any, Dict
import os
import structlog
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime

from config.settings import Settings  # Replace with mymate.config.settings if needed
from crew import ResearchWritingCrew  # Replace with mymate.crew.Mymate if needed

logger = structlog.get_logger(__name__)

class MessageHandler:
    """Handles Slack message processing and responses."""

    def __init__(self, app: App):
        self.app = app
        self.logger = structlog.get_logger(__name__)
        self.mymate = ResearchWritingCrew(Settings())  # Replace Settings with your settings import

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
            response = self.mymate.run(text)  # Adjusted to match ResearchWritingCrew; update if Mymate differs
            self._send_response(response, say, thread_ts)

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            say(text=f"Sorry, I encountered an error: {str(e)}", thread_ts=thread_ts)

    def _send_response(self, response: str, say: Any, thread_ts: str) -> None:
        """Send response message with rich text formatting and store in history."""
        # Default message if response is empty
        text_response = response if response else "Processing your request..."

        # Apply basic mrkdwn formatting
        formatted_response = self._format_response(text_response)

        # Send formatted response with mrkdwn enabled
        say(
            text=formatted_response,
            thread_ts=thread_ts,
            mrkdwn=True  # Enable mrkdwn parsing
        )

        # Store response in conversation history (simplified)
        message_data = {
            "text": formatted_response,
            "timestamp": datetime.now().isoformat(),
            "type": "outgoing"
        }
        self.logger.debug("Sent response", message_data=message_data)

    def _format_response(self, response: str) -> str:
        """Format the crew response with Slack mrkdwn syntax."""
        formatted_text = response.replace("**", "*")
        # Split response into lines for potential list formatting
        lines = formatted_text.split("\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Example: Bold the first line as a header
            if not formatted_lines:
                formatted_lines.append(f"*Response*\n{line}")
            # Treat lines starting with '-' or numbers as list items
            elif line.startswith("-"):
                formatted_lines.append(f"{line}")  # Bullet list
            elif line[0].isdigit() and line[1] == ".":
                formatted_lines.append(f"{line}")  # Numbered list
            else:
                formatted_lines.append(line)

        # Join lines with newlines and wrap in a code block if it’s code-like
        formatted_text = "\n".join(formatted_lines)
        if "```" in formatted_text:  # Preserve existing code blocks
            return formatted_text
        return formatted_text  # Return as-is for simple formatting

# Initialize the Slack app
settings = Settings()
app = App(token=settings.slack_bot_token)
message_handler = MessageHandler(app)

@app.event("message")
def handle_message(event: Dict[str, str], say, client) -> None:
    """Handle incoming messages."""
    logger.info("Received message event", slack_event=event)
    try:
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event.get("ts"))
        text = event.get("text", "")
        app_id = app.client.auth_test()["user_id"]
        logger.debug("Bot app_id", app_id=app_id)
        if not event.get("thread_ts") and f"<@{app_id}>" not in text:
            logger.info("Message not directed to bot, ignoring")
            return
        message_handler.process_message(text, say, thread_ts)
        logger.info("Message processed successfully")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}", exc_info=True)
        say(text="Sorry, I encountered an error processing your message.", thread_ts=thread_ts)

@app.event("app_mention")
def handle_app_mention(event: Dict[str, str], say) -> None:
    """Handle app mention events and delegate to message handler."""
    logger.info("Received app_mention event", slack_event=event)
    # thread_ts = event.get("thread_ts", event.get("ts"))
    # text = event.get("text", "")
    # message_handler.process_message(text, say, thread_ts)

class SlackApp:
    def start(self) -> None:
        """Start the Slack app with Socket Mode."""
        try:
            handler = SocketModeHandler(app=app, app_token=settings.slack_app_token)
            logger.info("Starting Slack app in Socket Mode")
            handler.start()
        except Exception as e:
            logger.error("Error starting Slack app", error=str(e))
            raise

if __name__ == "__main__":
    slack_app = SlackApp()
    slack_app.start()