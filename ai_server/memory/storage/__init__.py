"""Storage backend interface for session management."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ai_server.schemas.memory_models import SessionState


class StorageBackend(ABC):
    """Abstract base class for session storage backends."""
    
    @abstractmethod
    def save_session(self, session: SessionState) -> None:
        """Save a session to storage."""
        pass
    
    @abstractmethod
    def load_session(self, session_id: str) -> Optional[SessionState]:
        """Load a session from storage."""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session from storage."""
        pass
    
    @abstractmethod
    def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List all session IDs, optionally filtered by user_id."""
        pass
    
    @abstractmethod
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of deleted sessions."""
        pass
