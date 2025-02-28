import functools
import structlog
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from src.auth.role_manager import RoleManager, Operation

logger = structlog.get_logger(__name__)

# Type variable for function return type
T = TypeVar('T')

def requires_permission(operation: Operation) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to check if a user has permission to perform an operation.
    
    Args:
        operation: The operation to check permission for
        
    Returns:
        A decorator function that checks permissions
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract role_manager and user_id from kwargs
            role_manager = kwargs.get('role_manager')
            user_id = kwargs.get('user_id')
            
            # In tests, role_manager might be a Mock object, so we can't use isinstance directly
            if not role_manager:
                logger.error("Role manager not provided", 
                           operation=operation.name)
                raise ValueError("Role manager must be provided")
            
            if not user_id or not isinstance(user_id, str):
                logger.error("User ID not provided or invalid", 
                           operation=operation.name)
                raise ValueError("User ID must be provided")
            
            # Check if the user can perform the operation
            if role_manager.can_perform_operation(user_id, operation):
                logger.debug("Permission granted", 
                           user_id=user_id, 
                           operation=operation.name)
                return func(*args, **kwargs)
            else:
                logger.info("Permission denied, requires approval", 
                          user_id=user_id, 
                          operation=operation.name)
                # Return a special value or raise an exception to indicate approval needed
                raise PermissionError(f"Operation {operation.name} requires approval for user {user_id}")
        
        return cast(Callable[..., T], wrapper)
    
    return decorator

class ApprovalRequest:
    """Represents a request that needs approval."""
    
    def __init__(self, 
                 request_id: str,
                 user_id: str, 
                 operation: Operation, 
                 details: Dict[str, Any],
                 channel_id: str,
                 thread_ts: str):
        """
        Initialize an approval request.
        
        Args:
            request_id: Unique identifier for the request
            user_id: ID of the user making the request
            operation: The operation being requested
            details: Additional details about the request
            channel_id: ID of the channel where the request was made
            thread_ts: Thread timestamp of the request
        """
        self.request_id = request_id
        self.user_id = user_id
        self.operation = operation
        self.details = details
        self.channel_id = channel_id
        self.thread_ts = thread_ts
        self.status = "pending"  # pending, approved, denied
        self.approver_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the request to a dictionary for storage."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation": self.operation.name,
            "details": self.details,
            "channel_id": self.channel_id,
            "thread_ts": self.thread_ts,
            "status": self.status,
            "approver_id": self.approver_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalRequest':
        """Create an approval request from a dictionary."""
        request = cls(
            request_id=data["request_id"],
            user_id=data["user_id"],
            operation=Operation[data["operation"]],
            details=data["details"],
            channel_id=data["channel_id"],
            thread_ts=data["thread_ts"]
        )
        request.status = data["status"]
        request.approver_id = data["approver_id"]
        return request
