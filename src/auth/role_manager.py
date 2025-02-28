from enum import Enum, auto
import structlog
from typing import List, Optional
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class Role(Enum):
    """User role types."""
    ADMIN = auto()
    REGULAR = auto()

class Operation(Enum):
    """Operation types that may require permission checks."""
    # Document operations
    DOCUMENT_ADD = auto()
    DOCUMENT_DELETE = auto()
    DOCUMENT_UPDATE = auto()
    DOCUMENT_LIST = auto()
    DOCUMENT_VIEW = auto()
    DOCUMENT_STATS = auto()  # Added for viewing document statistics
    
    # Other operations can be added here as needed
    # For example:
    # USER_MANAGEMENT = auto()
    # SYSTEM_CONFIG = auto()

class RoleManager:
    """Manages user roles and permissions."""
    
    def __init__(self, settings: Settings):
        """
        Initialize the role manager.
        
        Args:
            settings: Application settings containing admin user IDs
        """
        self.settings = settings
        self.admin_user_ids = settings.admin_user_ids
        logger.info("Role manager initialized", admin_count=len(self.admin_user_ids))
    
    def get_user_role(self, user_id: str) -> Role:
        """
        Get the role for a user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            The user's role (ADMIN or REGULAR)
        """
        if user_id in self.admin_user_ids:
            return Role.ADMIN
        return Role.REGULAR
    
    def is_admin(self, user_id: str) -> bool:
        """
        Check if a user is an admin.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            True if the user is an admin, False otherwise
        """
        return user_id in self.admin_user_ids
    
    def can_perform_operation(self, user_id: str, operation: Operation) -> bool:
        """
        Check if a user can perform an operation directly.
        
        Args:
            user_id: Slack user ID
            operation: The operation to check
            
        Returns:
            True if the user can perform the operation directly, False if approval is needed
        """
        # Admin users can perform all operations directly
        if self.is_admin(user_id):
            return True
        
        # Regular users need approval for document management operations
        if operation in [Operation.DOCUMENT_ADD, Operation.DOCUMENT_DELETE, Operation.DOCUMENT_UPDATE]:
            return False
        
        # Regular users can perform other operations directly
        return True
    
    def requires_approval(self, user_id: str, operation: Operation) -> bool:
        """
        Check if an operation requires approval for a user.
        
        Args:
            user_id: Slack user ID
            operation: The operation to check
            
        Returns:
            True if the operation requires approval, False otherwise
        """
        return not self.can_perform_operation(user_id, operation)
