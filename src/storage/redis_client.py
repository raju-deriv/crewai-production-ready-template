import redis
import msgpack
from typing import Optional, Dict, Any, List
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

class RedisConnectionError(Exception):
    """Custom exception for Redis connection issues."""
    pass

class RedisConversationStore:
    """Handles storage and retrieval of conversation history in Redis."""

    def __init__(self, host: str, port: int, password: Optional[str] = None,
                 db: int = 0, ssl: bool = True, ttl: int = 86400):
        """Initialize Redis connection pool and configuration.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            ssl: Whether to use SSL
            ttl: Time to live for conversations in seconds (default: 1 day)
        """
        self.ttl = ttl
        connection_kwargs = {
            "host": host,
            "port": port,
            "password": password,
            "db": db,
            "decode_responses": False,  # We'll handle decoding with msgpack
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True
        }
        # Only add ssl if it's enabled
        if ssl:
            connection_kwargs["connection_class"] = redis.connection.SSLConnection

        self._pool = redis.ConnectionPool(**connection_kwargs)
        self._redis: Optional[redis.Redis] = None
        logger.info("Redis connection pool initialized", 
                   host=host, port=port, db=db, ssl=ssl)

    @property
    def redis(self) -> redis.Redis:
        """Get Redis client, creating it if necessary."""
        if self._redis is None:
            try:
                self._redis = redis.Redis(connection_pool=self._pool)
                self._redis.ping()  # Test connection
            except redis.RedisError as e:
                logger.error("Failed to connect to Redis", error=str(e))
                raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")
        return self._redis

    def store_message(self, channel_id: str, thread_ts: str, 
                     message: Dict[str, Any]) -> None:
        """Store a message in the conversation history.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            message: Message data including text, timestamp, and type
        """
        try:
            key = f"conversation:{channel_id}:{thread_ts}"
            
            # Add message metadata
            message["stored_at"] = datetime.now().isoformat()
            
            # Get existing messages
            existing = self.get_messages(channel_id, thread_ts)
            messages = existing + [message] if existing else [message]
            
            # Store updated conversation
            self.redis.setex(
                key,
                self.ttl,
                msgpack.packb(messages, use_bin_type=True)
            )
            
            logger.debug("Stored message in Redis",
                        channel=channel_id,
                        thread=thread_ts,
                        message_count=len(messages))
                        
        except (redis.RedisError, msgpack.PackException) as e:
            logger.error("Failed to store message", 
                        error=str(e),
                        channel=channel_id,
                        thread=thread_ts)
            raise RedisConnectionError(f"Failed to store message: {str(e)}")

    def get_messages(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of message dictionaries
        """
        try:
            key = f"conversation:{channel_id}:{thread_ts}"
            data = self.redis.get(key)
            
            if data:
                messages = msgpack.unpackb(data, raw=False)
                logger.debug("Retrieved messages from Redis",
                            channel=channel_id,
                            thread=thread_ts,
                            message_count=len(messages))
                return messages
            return []
            
        except (redis.RedisError, msgpack.UnpackException) as e:
            logger.error("Failed to retrieve messages", 
                        error=str(e),
                        channel=channel_id,
                        thread=thread_ts)
            raise RedisConnectionError(f"Failed to retrieve messages: {str(e)}")

    def extend_ttl(self, channel_id: str, thread_ts: str) -> None:
        """Extend the TTL for a conversation thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
        """
        try:
            key = f"conversation:{channel_id}:{thread_ts}"
            if self.redis.exists(key):
                self.redis.expire(key, self.ttl)
                logger.debug("Extended conversation TTL",
                            channel=channel_id,
                            thread=thread_ts,
                            ttl=self.ttl)
        except redis.RedisError as e:
            logger.error("Failed to extend conversation TTL",
                        error=str(e),
                        channel=channel_id,
                        thread=thread_ts)
            raise RedisConnectionError(f"Failed to extend TTL: {str(e)}")

    def cleanup_expired(self) -> None:
        """Cleanup any expired conversations.
        This is handled automatically by Redis TTL but this method
        can be used for manual cleanup if needed.
        """
        pass  # Redis handles TTL expiration automatically

    def close(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")
