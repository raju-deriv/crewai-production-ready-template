import json
import uuid
import structlog
from typing import Dict, List, Optional, Any
import redis
from src.auth.permissions import ApprovalRequest
from src.storage.redis_client import RedisConnectionError

logger = structlog.get_logger(__name__)

class ApprovalStore:
    """Store for managing approval requests."""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6379, 
                 password: Optional[str] = None,
                 db: int = 0,
                 ssl: bool = False,
                 ttl: int = 86400):  # Default TTL: 1 day
        """
        Initialize the approval store.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            ssl: Whether to use SSL
            ttl: Time-to-live for approval requests in seconds
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.ssl = ssl
        self.ttl = ttl
        self.prefix = "approval:"
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                ssl=self.ssl,
                decode_responses=True
            )
            self.redis.ping()  # Test connection
            logger.info("Connected to Redis for approval store", 
                       host=self.host, 
                       port=self.port, 
                       db=self.db)
        except redis.RedisError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")
    
    def create_request(self, 
                      user_id: str, 
                      operation: str, 
                      details: Dict[str, Any],
                      channel_id: str,
                      thread_ts: str) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            user_id: ID of the user making the request
            operation: The operation being requested
            details: Additional details about the request
            channel_id: ID of the channel where the request was made
            thread_ts: Thread timestamp of the request
            
        Returns:
            The created approval request
        """
        from src.auth.role_manager import Operation
        
        # Generate a unique ID for the request
        request_id = str(uuid.uuid4())
        
        # Create the approval request
        request = ApprovalRequest(
            request_id=request_id,
            user_id=user_id,
            operation=Operation[operation],
            details=details,
            channel_id=channel_id,
            thread_ts=thread_ts
        )
        
        # Store the request in Redis
        key = f"{self.prefix}{request_id}"
        try:
            self.redis.set(key, json.dumps(request.to_dict()), ex=self.ttl)
            logger.info("Created approval request", 
                       request_id=request_id, 
                       user_id=user_id, 
                       operation=operation)
            return request
        except redis.RedisError as e:
            logger.error("Failed to store approval request", 
                       error=str(e), 
                       request_id=request_id)
            raise RedisConnectionError(f"Failed to store approval request: {str(e)}")
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get an approval request by ID.
        
        Args:
            request_id: ID of the request
            
        Returns:
            The approval request, or None if not found
        """
        key = f"{self.prefix}{request_id}"
        try:
            data = self.redis.get(key)
            if data:
                return ApprovalRequest.from_dict(json.loads(data))
            return None
        except redis.RedisError as e:
            logger.error("Failed to get approval request", 
                       error=str(e), 
                       request_id=request_id)
            raise RedisConnectionError(f"Failed to get approval request: {str(e)}")
    
    def update_request(self, request: ApprovalRequest) -> None:
        """
        Update an approval request.
        
        Args:
            request: The request to update
        """
        key = f"{self.prefix}{request.request_id}"
        try:
            self.redis.set(key, json.dumps(request.to_dict()), ex=self.ttl)
            logger.info("Updated approval request", 
                       request_id=request.request_id, 
                       status=request.status)
        except redis.RedisError as e:
            logger.error("Failed to update approval request", 
                       error=str(e), 
                       request_id=request.request_id)
            raise RedisConnectionError(f"Failed to update approval request: {str(e)}")
    
    def approve_request(self, request_id: str, approver_id: str) -> Optional[ApprovalRequest]:
        """
        Approve an approval request.
        
        Args:
            request_id: ID of the request
            approver_id: ID of the approver
            
        Returns:
            The updated approval request, or None if not found
        """
        request = self.get_request(request_id)
        if not request:
            return None
        
        request.status = "approved"
        request.approver_id = approver_id
        self.update_request(request)
        return request
    
    def deny_request(self, request_id: str, approver_id: str) -> Optional[ApprovalRequest]:
        """
        Deny an approval request.
        
        Args:
            request_id: ID of the request
            approver_id: ID of the approver
            
        Returns:
            The updated approval request, or None if not found
        """
        request = self.get_request(request_id)
        if not request:
            return None
        
        request.status = "denied"
        request.approver_id = approver_id
        self.update_request(request)
        return request
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """
        Get all pending approval requests.
        
        Returns:
            List of pending approval requests
        """
        try:
            # Get all keys with the approval prefix
            keys = self.redis.keys(f"{self.prefix}*")
            requests = []
            
            for key in keys:
                data = self.redis.get(key)
                if data:
                    request = ApprovalRequest.from_dict(json.loads(data))
                    if request.status == "pending":
                        requests.append(request)
            
            return requests
        except redis.RedisError as e:
            logger.error("Failed to get pending approval requests", error=str(e))
            raise RedisConnectionError(f"Failed to get pending approval requests: {str(e)}")
    
    def close(self) -> None:
        """Close the Redis connection."""
        try:
            if hasattr(self, 'redis'):
                self.redis.close()
                logger.info("Closed Redis connection for approval store")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
