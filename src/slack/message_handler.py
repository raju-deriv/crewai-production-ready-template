from typing import Any, Dict, List
from datetime import datetime
import structlog
from src.crew.base_crew import BaseCrew
from src.utils.formatting import format_slack_message
from src.storage.redis_client import RedisConversationStore, RedisConnectionError
from src.storage.approval_store import ApprovalStore
from src.auth.role_manager import RoleManager, Operation

logger = structlog.get_logger(__name__)

class MessageHandler:
    """Handles Slack message processing and responses."""

    def __init__(self, crew: BaseCrew, conversation_store: RedisConversationStore, 
                role_manager: RoleManager, approval_store: ApprovalStore):
        self.crew = crew
        self.conversation_store = conversation_store
        self.role_manager = role_manager
        self.approval_store = approval_store
        self.logger = structlog.get_logger(__name__)

    def process_message(self, text: str, say: Any, thread_ts: str, channel_id: str, user_id: str, client: Any = None) -> None:
        """
        Process incoming messages and handle responses.
        
        Args:
            text: The message text
            say: Function to send a message
            thread_ts: Thread timestamp
            channel_id: Channel ID
            user_id: User ID of the sender
            client: Slack client
        """
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
            
            # Run the crew task with conversation history and user ID
            inputs = {
                "topic": text,
                "conversation_history": history,
                "user_id": user_id,
                "channel_id": channel_id
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
            response = self.crew.run(inputs={
                "topic": text,
                "user_id": user_id,
                "channel_id": channel_id
            })
            
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
    
    def create_approval_request(self, 
                               user_id: str, 
                               operation: str, 
                               details: Dict[str, Any],
                               channel_id: str,
                               thread_ts: str,
                               say: Any,
                               client: Any) -> None:
        """
        Create an approval request and notify admins.
        
        Args:
            user_id: ID of the user making the request
            operation: The operation being requested
            details: Additional details about the request
            channel_id: ID of the channel where the request was made
            thread_ts: Thread timestamp of the request
            say: Function to send a message
            client: Slack client
        """
        try:
            # Create the approval request
            request = self.approval_store.create_request(
                user_id=user_id,
                operation=operation,
                details=details,
                channel_id=channel_id,
                thread_ts=thread_ts
            )
            
            # Notify the user that their request requires approval
            self._send_response(
                "Your request requires admin approval. An admin will be notified.",
                say,
                thread_ts,
                channel_id
            )
            
            # Notify admins about the request
            self._notify_admins_of_approval_request(request, client)
            
        except Exception as e:
            self.logger.error("Failed to create approval request", error=str(e), exc_info=True)
            self._send_response(
                f"Sorry, I encountered an error processing your approval request: {str(e)}",
                say,
                thread_ts,
                channel_id
            )
    
    def _notify_admins_of_approval_request(self, request: Any, client: Any) -> None:
        """
        Notify admins about an approval request.
        
        Args:
            request: The approval request
            client: Slack client
        """
        # For each admin user, send a direct message with approval buttons
        for admin_id in self.role_manager.admin_user_ids:
            try:
                # Open a DM with the admin
                response = client.conversations_open(users=admin_id)
                dm_channel_id = response["channel"]["id"]
                
                # Create the approval message with buttons
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Approval Request*\n\nUser <@{request.user_id}> has requested to perform operation: *{request.operation.name}*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Details:*\n```{str(request.details)}```"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Approve",
                                    "emoji": True
                                },
                                "style": "primary",
                                "value": request.request_id,
                                "action_id": f"approve_request_{request.request_id}"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Deny",
                                    "emoji": True
                                },
                                "style": "danger",
                                "value": request.request_id,
                                "action_id": f"deny_request_{request.request_id}"
                            }
                        ]
                    }
                ]
                
                # Send the message
                client.chat_postMessage(
                    channel=dm_channel_id,
                    text=f"Approval request from <@{request.user_id}>",
                    blocks=blocks
                )
                
                self.logger.info("Sent approval request notification", 
                               admin_id=admin_id, 
                               request_id=request.request_id)
                
            except Exception as e:
                self.logger.error("Failed to notify admin of approval request", 
                               error=str(e), 
                               admin_id=admin_id,
                               request_id=request.request_id)
    
    def handle_approval_response(self, 
                                request_id: str, 
                                approver_id: str, 
                                approved: bool,
                                client: Any) -> None:
        """
        Handle an admin's response to an approval request.
        
        Args:
            request_id: ID of the request
            approver_id: ID of the admin who responded
            approved: Whether the request was approved
            client: Slack client
        """
        try:
            # Get the request from the store
            if approved:
                request = self.approval_store.approve_request(request_id, approver_id)
            else:
                request = self.approval_store.deny_request(request_id, approver_id)
            
            if not request:
                self.logger.error("Approval request not found", request_id=request_id)
                return
            
            # Notify the user of the approval status
            self._notify_user_of_approval_status(request, approved, client)
            
            # If approved, execute the requested operation
            if approved:
                self._execute_approved_operation(request, client)
            
        except Exception as e:
            self.logger.error("Failed to handle approval response", 
                           error=str(e), 
                           request_id=request_id,
                           approver_id=approver_id,
                           approved=approved)
    
    def _notify_user_of_approval_status(self, request: Any, approved: bool, client: Any) -> None:
        """
        Notify the user of the approval status.
        
        Args:
            request: The approval request
            approved: Whether the request was approved
            client: Slack client
        """
        try:
            status = "approved" if approved else "denied"
            message = f"Your request to perform operation *{request.operation.name}* has been {status} by an admin."
            
            # Send a message in the original thread
            client.chat_postMessage(
                channel=request.channel_id,
                thread_ts=request.thread_ts,
                text=message,
                mrkdwn=True
            )
            
            self.logger.info("Notified user of approval status", 
                           user_id=request.user_id, 
                           request_id=request.request_id,
                           status=status)
            
        except Exception as e:
            self.logger.error("Failed to notify user of approval status", 
                           error=str(e), 
                           user_id=request.user_id,
                           request_id=request.request_id)
    
    def _execute_approved_operation(self, request: Any, client: Any) -> None:
        """
        Execute the approved operation.
        
        Args:
            request: The approval request
            client: Slack client
        """
        try:
            # Extract operation and details
            operation = request.operation
            details = request.details
            
            self.logger.info("Executing approved operation", 
                           operation=operation.name, 
                           request_id=request.request_id)
            
            # Execute the operation based on its type
            result = None
            
            # Check which operation type it is and execute accordingly
            if operation in [Operation.LIST_DOCUMENTS, Operation.READ_DOCUMENT, 
                           Operation.DELETE_DOCUMENT, Operation.VIEW_STATS]:
                # Get the document management tool from the crew
                doc_tool = self.crew.get_tool("manage_documents")
                if doc_tool:
                    result = doc_tool.execute_approved_operation(operation, details)
                else:
                    self.logger.error("Document management tool not found in crew")
                    result = "Error: Document management tool not available"
            else:
                self.logger.warning("Unsupported operation type", operation=operation.name)
                result = f"Unsupported operation type: {operation.name}"
            
            # Notify the user of the result
            client.chat_postMessage(
                channel=request.channel_id,
                thread_ts=request.thread_ts,
                text=f"The operation *{operation.name}* has been executed:\n\n{result}",
                mrkdwn=True
            )
            
        except Exception as e:
            self.logger.error("Failed to execute approved operation", 
                           error=str(e), 
                           operation=request.operation.name,
                           request_id=request.request_id)
            
            # Notify the user of the failure
            client.chat_postMessage(
                channel=request.channel_id,
                thread_ts=request.thread_ts,
                text=f"Sorry, I encountered an error executing the approved operation: {str(e)}",
                mrkdwn=True
            )
