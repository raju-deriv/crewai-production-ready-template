from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.config.settings import Settings
from src.slack.message_handler import MessageHandler
from src.crew.base_crew import BaseCrew
from typing import Dict, Any, Callable
import structlog

logger = structlog.get_logger(__name__)

class SlackApp:
    """Slack application with event handlers and message processing."""

    def __init__(self, settings: Settings, crew: BaseCrew):
        self.settings = settings
        self.app = App(token=settings.slack_bot_token)
        self.message_handler = MessageHandler(crew)
        # Store handlers for test access
        self.handle_message: Callable[[Dict[str, str], Any, Any], None] = None
        self.handle_app_mention: Callable[[Dict[str, str], Any], None] = None
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register Slack event handlers and store them for testing."""

        @self.app.event("message")
        def handle_message(event: Dict[str, str], say, client) -> None:
            logger.info("Received message event", slack_event=event)
            try:
                channel_id = event.get("channel")
                thread_ts = event.get("thread_ts", event.get("ts"))
                text = event.get("text", "")
                app_id = self.app.client.auth_test()["user_id"]
                logger.debug("Bot app_id", app_id=app_id)
                if not event.get("thread_ts") and f"<@{app_id}>" not in text:
                    logger.info("Message not directed to bot, ignoring")
                    return
                self.message_handler.process_message(text, say, thread_ts)
                logger.info("Message processed successfully")
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}", exc_info=True)
                say(text="Sorry, I encountered an error processing your message.", thread_ts=thread_ts)
        
        # Store the handler function
        self.handle_message = handle_message

        @self.app.event("app_mention")
        def handle_app_mention(event: Dict[str, str], say) -> None:
            logger.info("Received app_mention event", slack_event=event)
        
        # Store the handler function
        self.handle_app_mention = handle_app_mention

    def start(self) -> None:
        """Start the Slack app with Socket Mode."""
        try:
            handler = SocketModeHandler(app=self.app, app_token=self.settings.slack_app_token)
            logger.info("Starting Slack app in Socket Mode")
            handler.start()
        except Exception as e:
            logger.error("Error starting Slack app", error=str(e), exc_info=True)
            raise