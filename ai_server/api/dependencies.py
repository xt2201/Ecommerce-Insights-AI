
from typing import Generator, Optional
from fastapi import Depends, HTTPException
from ai_server.memory.session_manager import SessionManager
from ai_server.core.config import get_config_value

# Global session manager instance
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """Dependency to get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        # Initialize if not already done (should be done in lifespan)
        _session_manager = SessionManager()
    return _session_manager

def init_dependencies():
    """Initialize global dependencies"""
    global _session_manager
    db_path = get_config_value("memory.storage.sqlite.db_path", "data/sessions.db")
    _session_manager = SessionManager()
