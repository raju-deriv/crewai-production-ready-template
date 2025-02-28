from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.config.settings import Settings
from src.slack.message_handler import MessageHandler
from src.crew.base_crew import BaseCrew
from src.storage.redis_client import RedisConversationStore
from src.storage.approval_store import ApprovalStore
from src.auth.role_manager import RoleManager
from typing import Dict, Any, Callable
import structlog
import atexit
import re

logger = structlog.get_logger(__name__)

class SlackApp:
    """Slack application with event handlers and message processing."""

    def __init__(self, settings: Settings, crew: BaseCrew):
        self.settings = settings
        self.app = App(token=settings.slack_bot_token)
        
        # Initialize Redis conversation store
        self.conversation_store = RedisConversationStore(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            ssl=settings.redis_ssl,
            ttl=settings.redis_ttl
        )
        
        # Initialize approval store
        self.approval_store = ApprovalStore(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            ssl=settings.redis_ssl,
            ttl=settings.redis_ttl
        )
        
        # Initialize role manager
        self.role_manager = RoleManager(settings)
        
        # Register cleanup on exit
        atexit.register(self._cleanup)
        
        self.message_handler = MessageHandler(
            crew=crew, 
            conversation_store=self.conversation_store,
            role_manager=self.role_manager,
            approval_store=self.approval_store
        )
        # Store handlers for test access
        self.handle_message: Callable[[Dict[str, str], Any, Any], None] = None
        self.handle_app_mention: Callable[[Dict[str, str], Any], None] = None
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register Slack event handlers and store them for testing."""
        self._register_message_handlers()
        self._register_action_handlers()
        
    def _register_message_handlers(self) -> None:
        """Register message event handlers."""

        @self.app.event("message")
        def handle_message(event: Dict[str, str], say, client) -> None:
            logger.info("Received message event", slack_event=event)
            try:
                channel_id = event.get("channel")
                thread_ts = event.get("thread_ts", event.get("ts"))
                text = event.get("text", "")
                user_id = event.get("user", "unknown_user")
                app_id = self.app.client.auth_test()["user_id"]
                logger.debug("Bot app_id", app_id=app_id)
                if not event.get("thread_ts") and f"<@{app_id}>" not in text:
                    logger.info("Message not directed to bot, ignoring")
                    return
                self.message_handler.process_message(
                    text=text,
                    say=say,
                    thread_ts=thread_ts,
                    channel_id=channel_id,
                    user_id=user_id,
                    client=client
                )
                logger.info("Message processed successfully")
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}", exc_info=True)
                say(text="Sorry, I encountered an error processing your message.", thread_ts=thread_ts)
        
        # Store the handler function
        self.handle_message = handle_message

        @self.app.event("app_mention")
        def handle_app_mention(event: Dict[str, str], say, client) -> None:
            logger.info("Received app_mention event", slack_event=event)
            try:
                channel_id = event.get("channel")
                thread_ts = event.get("ts")  # App mentions don't have thread_ts
                text = event.get("text", "")
                user_id = event.get("user", "unknown_user")
                
                # Just log the event, no processing
                
                logger.info("App mention processed successfully")
            except Exception as e:
                logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
                say(text="Sorry, I encountered an error processing your message.", thread_ts=thread_ts)
        
        # Store the handler function
        self.handle_app_mention = handle_app_mention
    
    def _register_action_handlers(self) -> None:
        """Register action handlers for interactive components."""
        
        # Handler for approval button actions
        @self.app.action(re.compile(r"approve_request_.*"))
        def handle_approve_action(ack, body, client) -> None:
            ack()  # Acknowledge the action
            
            try:
                # Extract the request ID from the action ID
                action_id = body["actions"][0]["action_id"]
                request_id = action_id.replace("approve_request_", "")
                
                # Get the user ID of the approver
                approver_id = body["user"]["id"]
                
                logger.info("Received approval action", 
                           request_id=request_id, 
                           approver_id=approver_id)
                
                # Check if the approver is an admin
                if not self.role_manager.is_admin(approver_id):
                    logger.warning("Non-admin user attempted to approve request", 
                                 approver_id=approver_id, 
                                 request_id=request_id)
                    
                    # Update the message to indicate the action was denied
                    client.chat_update(
                        channel=body["channel"]["id"],
                        ts=body["message"]["ts"],
                        text="You do not have permission to approve requests.",
                        blocks=[]
                    )
                    return
                
                # Handle the approval
                self.message_handler.handle_approval_response(
                    request_id=request_id,
                    approver_id=approver_id,
                    approved=True,
                    client=client
                )
                
                # Update the message to indicate the action was taken
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text=f"Request {request_id} has been approved by <@{approver_id}>.",
                    blocks=[]
                )
                
            except Exception as e:
                logger.error("Error handling approval action", error=str(e), exc_info=True)
                
                # Update the message to indicate an error occurred
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text=f"Error processing approval: {str(e)}",
                    blocks=[]
                )
        
        # Handler for denial button actions
        @self.app.action(re.compile(r"deny_request_.*"))
        def handle_deny_action(ack, body, client) -> None:
            ack()  # Acknowledge the action
            
            try:
                # Extract the request ID from the action ID
                action_id = body["actions"][0]["action_id"]
                request_id = action_id.replace("deny_request_", "")
                
                # Get the user ID of the denier
                approver_id = body["user"]["id"]
                
                logger.info("Received denial action", 
                           request_id=request_id, 
                           approver_id=approver_id)
                
                # Check if the approver is an admin
                if not self.role_manager.is_admin(approver_id):
                    logger.warning("Non-admin user attempted to deny request", 
                                 approver_id=approver_id, 
                                 request_id=request_id)
                    
                    # Update the message to indicate the action was denied
                    client.chat_update(
                        channel=body["channel"]["id"],
                        ts=body["message"]["ts"],
                        text="You do not have permission to deny requests.",
                        blocks=[]
                    )
                    return
                
                # Handle the denial
                self.message_handler.handle_approval_response(
                    request_id=request_id,
                    approver_id=approver_id,
                    approved=False,
                    client=client
                )
                
                # Update the message to indicate the action was taken
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text=f"Request {request_id} has been denied by <@{approver_id}>.",
                    blocks=[]
                )
                
            except Exception as e:
                logger.error("Error handling denial action", error=str(e), exc_info=True)
                
                # Update the message to indicate an error occurred
                client.chat_update(
                    channel=body["channel"]["id"],
                    ts=body["message"]["ts"],
                    text=f"Error processing denial: {str(e)}",
                    blocks=[]
                )

    def start(self) -> None:
        """Start the Slack app with Socket Mode."""
        try:
            handler = SocketModeHandler(app=self.app, app_token=self.settings.slack_app_token)
            logger.info("Starting Slack app in Socket Mode")
            handler.start()
        except Exception as e:
            logger.error("Error starting Slack app", error=str(e), exc_info=True)
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        try:
            if hasattr(self, 'conversation_store'):
                self.conversation_store.close()
                logger.info("Closed conversation store Redis connection")
            
            if hasattr(self, 'approval_store'):
                self.approval_store.close()
                logger.info("Closed approval store Redis connection")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
