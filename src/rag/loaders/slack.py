import structlog
import os
import hashlib
import json
import tempfile
from typing import Dict, List, Any, Optional, Union
from src.rag.loaders.base import DocumentLoader
from src.rag.loaders.file import FileLoader
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class SlackLoader(DocumentLoader):
    """
    Loader for Slack messages and files.
    
    This class implements the DocumentLoader interface for Slack.
    It provides methods for loading documents from Slack messages and files.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the SlackLoader.
        
        Args:
            settings: Application settings containing Slack configuration.
        """
        self.settings = settings
        self.slack_bot_token = settings.slack_bot_token
        self.file_loader = FileLoader()
        
        logger.info("Initialized SlackLoader")
    
    def load(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Load a document from a Slack message or file.
        
        Args:
            source: Slack message ID or file ID.
            **kwargs: Additional arguments:
                - channel_id: Slack channel ID (required)
                - is_file: Whether the source is a file ID (default: False)
                - include_thread: Whether to include thread replies (default: True)
        
        Returns:
            Dict[str, Any]: The loaded document.
        """
        channel_id = kwargs.get('channel_id')
        is_file = kwargs.get('is_file', False)
        include_thread = kwargs.get('include_thread', True)
        
        if not channel_id:
            raise ValueError("channel_id is required for Slack loader")
        
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            # Initialize Slack client
            client = WebClient(token=self.slack_bot_token)
            
            if is_file:
                # Load file
                return self._load_file(client, source, channel_id)
            else:
                # Load message
                return self._load_message(client, source, channel_id, include_thread)
        except ImportError:
            logger.error("slack_sdk not installed, cannot load Slack messages or files")
            raise ImportError("slack_sdk not installed, cannot load Slack messages or files")
        except Exception as e:
            logger.error(f"Error loading Slack {'file' if is_file else 'message'}: {source}", error=str(e))
            # Return empty document with error metadata
            return {
                'id': f"slack_{hashlib.md5(source.encode()).hexdigest()}",
                'text': '',
                'metadata': {
                    'source': source,
                    'channel_id': channel_id,
                    'error': str(e),
                    'source_type': 'slack'
                }
            }
    
    def load_batch(self, sources: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Load multiple documents from Slack messages or files.
        
        Args:
            sources: List of Slack message IDs or file IDs.
            **kwargs: Additional arguments passed to load().
        
        Returns:
            List[Dict[str, Any]]: List of loaded documents.
        """
        documents = []
        
        for source in sources:
            document = self.load(source, **kwargs)
            documents.append(document)
        
        logger.info(f"Loaded {len(documents)} Slack {'files' if kwargs.get('is_file', False) else 'messages'}")
        return documents
    
    def supports(self, source_type: str) -> bool:
        """
        Check if the loader supports a source type.
        
        Args:
            source_type: Type of source.
        
        Returns:
            bool: True if the loader supports the source type, False otherwise.
        """
        return source_type.lower() in ['slack', 'slack_message', 'slack_file']
    
    def _load_message(self, client, message_ts: str, channel_id: str, include_thread: bool) -> Dict[str, Any]:
        """
        Load a Slack message.
        
        Args:
            client: Slack WebClient.
            message_ts: Slack message timestamp.
            channel_id: Slack channel ID.
            include_thread: Whether to include thread replies.
        
        Returns:
            Dict[str, Any]: The loaded document.
        """
        from slack_sdk.errors import SlackApiError
        
        try:
            # Get message
            response = client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                limit=1,
                inclusive=True
            )
            
            if not response['messages']:
                raise ValueError(f"Message not found: {message_ts}")
            
            message = response['messages'][0]
            text = message.get('text', '')
            
            # Get thread replies if requested
            thread_text = ""
            if include_thread and message.get('thread_ts'):
                thread_response = client.conversations_replies(
                    channel=channel_id,
                    ts=message.get('thread_ts'),
                    limit=100
                )
                
                # Skip the first message if it's the same as the main message
                start_idx = 1 if thread_response['messages'][0].get('ts') == message_ts else 0
                
                for reply in thread_response['messages'][start_idx:]:
                    user_info = client.users_info(user=reply.get('user', ''))
                    user_name = user_info['user'].get('real_name', user_info['user'].get('name', 'Unknown'))
                    thread_text += f"{user_name}: {reply.get('text', '')}\n\n"
            
            # Combine main message and thread
            if thread_text:
                text += f"\n\nThread replies:\n{thread_text}"
            
            # Get user info
            user_info = client.users_info(user=message.get('user', ''))
            user_name = user_info['user'].get('real_name', user_info['user'].get('name', 'Unknown'))
            
            # Generate document ID
            doc_id = f"slack_msg_{hashlib.md5((channel_id + message_ts).encode()).hexdigest()}"
            
            return {
                'id': doc_id,
                'text': text,
                'metadata': {
                    'source': message_ts,
                    'channel_id': channel_id,
                    'user': user_name,
                    'timestamp': message.get('ts', ''),
                    'has_thread': bool(thread_text),
                    'source_type': 'slack'
                }
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {str(e)}")
            raise
    
    def _load_file(self, client, file_id: str, channel_id: str) -> Dict[str, Any]:
        """
        Load a Slack file.
        
        Args:
            client: Slack WebClient.
            file_id: Slack file ID.
            channel_id: Slack channel ID.
        
        Returns:
            Dict[str, Any]: The loaded document.
        """
        from slack_sdk.errors import SlackApiError
        
        try:
            # Get file info
            file_info = client.files_info(file=file_id)
            file_data = file_info['file']
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_data.get('filetype', 'txt')}") as temp_file:
                temp_path = temp_file.name
            
            # Download file
            client.files_download(file=file_id, filename=temp_path)
            
            # Load file using FileLoader
            document = self.file_loader.load(temp_path)
            
            # Add Slack-specific metadata
            document['metadata'].update({
                'source': file_id,
                'channel_id': channel_id,
                'user': file_data.get('user', ''),
                'filename': file_data.get('name', ''),
                'filetype': file_data.get('filetype', ''),
                'timestamp': file_data.get('timestamp', ''),
                'source_type': 'slack'
            })
            
            # Generate document ID
            doc_id = f"slack_file_{hashlib.md5((channel_id + file_id).encode()).hexdigest()}"
            document['id'] = doc_id
            
            # Clean up temporary file
            os.remove(temp_path)
            
            return document
        except SlackApiError as e:
            logger.error(f"Slack API error: {str(e)}")
            raise
