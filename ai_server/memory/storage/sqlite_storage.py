"""SQLite storage backend for session management."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ai_server.memory.storage import StorageBackend
from ai_server.schemas.memory_models import SessionState


class SQLiteStorage(StorageBackend):
    """SQLite-based session storage backend."""
    
    def __init__(self, db_path: str = "data/sessions.db"):
        """Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT DEFAULT '',
                    session_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)
            """)
            
            # Migration: Add title column if it doesn't exist
            try:
                cursor = conn.execute("PRAGMA table_info(sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'title' not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT DEFAULT ''")
            except Exception:
                pass  # Column might already exist
            
            conn.commit()
    
    def save_session(self, session: SessionState) -> None:
        """Save a session to SQLite."""
        session_data = json.dumps(session.to_dict())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, user_id, title, session_data, created_at, updated_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.user_id,
                session.title,
                session_data,
                session.created_at.isoformat(),
                datetime.now().isoformat(),
                session.expires_at.isoformat() if session.expires_at else None,
                1 if session.is_active else 0
            ))
            conn.commit()
    
    def load_session(self, session_id: str) -> Optional[SessionState]:
        """Load a session from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_data FROM sessions 
                WHERE session_id = ? AND is_active = 1
            """, (session_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            session_dict = json.loads(row[0])
            return SessionState.from_dict(session_dict)
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title.
        
        Args:
            session_id: ID of the session to update
            title: New title for the session
            
        Returns:
            True if successful, False if session not found
        """
        with sqlite3.connect(self.db_path) as conn:
            # Update title column for fast access
            cursor = conn.execute("""
                UPDATE sessions SET title = ?, updated_at = ?
                WHERE session_id = ? AND is_active = 1
            """, (title, datetime.now().isoformat(), session_id))
            
            if cursor.rowcount == 0:
                return False
            
            # Also update in session_data for consistency
            cursor = conn.execute("""
                SELECT session_data FROM sessions 
                WHERE session_id = ? AND is_active = 1
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                session_dict = json.loads(row[0])
                session_dict['title'] = title
                conn.execute("""
                    UPDATE sessions SET session_data = ?
                    WHERE session_id = ?
                """, (json.dumps(session_dict), session_id))
            
            conn.commit()
            return True
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET is_active = 0 
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """List all active session IDs."""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    SELECT session_id FROM sessions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY updated_at DESC
                """, (user_id,))
            else:
                cursor = conn.execute("""
                    SELECT session_id FROM sessions 
                    WHERE is_active = 1
                    ORDER BY updated_at DESC
                """)
            
            return [row[0] for row in cursor.fetchall()]
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions SET is_active = 0 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            conn.commit()
            return cursor.rowcount
    
    def list_all_sessions(self, limit: int = 100, offset: int = 0, user_id: Optional[str] = None) -> List[SessionState]:
        """List all active sessions with full details.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            user_id: Optional user_id filter
            
        Returns:
            List of SessionState objects
        """
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    SELECT session_data FROM sessions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT session_data FROM sessions 
                    WHERE is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            sessions = []
            for row in cursor.fetchall():
                session_dict = json.loads(row[0])
                sessions.append(SessionState.from_dict(session_dict))
            
            return sessions
    
    def count_total_sessions(self, user_id: Optional[str] = None) -> int:
        """Count total number of active sessions.
        
        Args:
            user_id: Optional user_id filter
            
        Returns:
            Count of active sessions
        """
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM sessions 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
            else:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM sessions 
                    WHERE is_active = 1
                """)
            
            return cursor.fetchone()[0]
    
    def count_active_sessions(self) -> int:
        """Count active sessions (alias for count_total_sessions)."""
        return self.count_total_sessions()

    def clear_all_sessions(self) -> int:
        """Clear all sessions (mark as inactive).
        
        Returns:
            Number of sessions cleared
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions SET is_active = 0 
                WHERE is_active = 1
            """)
            conn.commit()
            return cursor.rowcount
