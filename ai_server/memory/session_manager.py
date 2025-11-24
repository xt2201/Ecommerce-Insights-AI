"""Session manager for handling user sessions and memory."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from ai_server.core.config import get_config_value
from ai_server.memory.storage.sqlite_storage import SQLiteStorage
from ai_server.schemas.memory_models import ConversationHistory, SessionState, UserPreferences


class SessionManager:
    """Manages user sessions with conversation history and preferences."""
    
    def __init__(self, storage_backend: Optional[SQLiteStorage] = None):
        """Initialize session manager.
        
        Args:
            storage_backend: Storage backend for sessions (defaults to SQLite)
        """
        if storage_backend is None:
            db_path = get_config_value("memory.storage.sqlite.db_path", "data/sessions.db")
            storage_backend = SQLiteStorage(db_path)
        
        self.storage = storage_backend
        self.default_ttl = get_config_value("memory.session.default_ttl", 3600)
    
    def create_session(self, user_id: Optional[str] = None, ttl: Optional[int] = None) -> SessionState:
        """Create a new session.
        
        Args:
            user_id: Optional user identifier
            ttl: Session time-to-live in seconds (defaults to config value)
            
        Returns:
            New SessionState object
        """
        session_id = str(uuid.uuid4())
        session_ttl = ttl if ttl is not None else self.default_ttl
        
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            conversation_history=ConversationHistory(session_id=session_id),
            user_preferences=UserPreferences(session_id=session_id),
            expires_at=datetime.now() + timedelta(seconds=session_ttl),
        )
        
        self.storage.save_session(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get an existing session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionState if found and not expired, None otherwise
        """
        session = self.storage.load_session(session_id)
        
        if session is None:
            return None
        
        # Check if expired
        if session.is_expired():
            self.delete_session(session_id)
            return None
        
        return session
    
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> SessionState:
        """Get existing session or create new one.
        
        Args:
            session_id: Optional session identifier
            user_id: Optional user identifier
            
        Returns:
            SessionState object (existing or new)
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(user_id=user_id)
    
    def update_session(self, session: SessionState) -> None:
        """Update an existing session.
        
        Args:
            session: SessionState to update
        """
        self.storage.save_session(session)
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session.
        
        Args:
            session_id: Session identifier
        """
        self.storage.delete_session(session_id)
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            Number of sessions deleted
        """
        return self.storage.cleanup_expired_sessions()
