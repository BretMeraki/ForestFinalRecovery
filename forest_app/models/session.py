"""
Session state management models for Forest App.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SessionState:
    """
    Represents the current state of a user session in Forest App.
    """
    
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    # Session data
    current_tree_id: Optional[str] = None
    current_node_id: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """Update the last active timestamp."""
        self.last_active = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Mark the session as inactive."""
        self.is_active = False
        self.update_activity()
    
    def activate(self) -> None:
        """Mark the session as active."""
        self.is_active = True
        self.update_activity()


__all__ = ["SessionState"] 