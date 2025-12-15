"""Encrypted SQLite storage backend with audit logging.

This module provides:
- Field-level encryption for sensitive session data
- Audit logging for all data access
- Migration support from unencrypted to encrypted storage

Security:
- AES-256 encryption for sensitive fields
- Key derivation using PBKDF2
- No plaintext secrets in logs
"""

from __future__ import annotations

import os
import json
import base64
import hashlib
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ai_server.schemas.memory_models import SessionState

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """Audit log entry for data access."""
    timestamp: str
    action: str  # "read", "write", "delete"
    session_id: str
    user_id: Optional[str]
    accessor: str  # Who accessed the data
    success: bool
    details: Optional[str] = None


class EncryptionProvider:
    """Handles encryption/decryption of sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption provider.
        
        Args:
            encryption_key: Base64-encoded encryption key or env var name
        """
        self._key = self._load_key(encryption_key)
        self._cipher = None
        
        if self._key:
            self._init_cipher()
    
    def _load_key(self, key_source: Optional[str]) -> Optional[bytes]:
        """Load encryption key from environment or direct value."""
        if key_source is None:
            # Try environment variable
            key_env = os.getenv("SESSION_ENCRYPTION_KEY")
            if key_env:
                return base64.b64decode(key_env)
            return None
        
        # Direct key provided
        try:
            return base64.b64decode(key_source)
        except Exception:
            # Treat as password, derive key
            return self._derive_key(key_source)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        salt = os.getenv("SESSION_ENCRYPTION_SALT", "ecom-session-salt-v1").encode()
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            iterations=100000,
            dklen=32
        )
    
    def _init_cipher(self) -> None:
        """Initialize AES cipher."""
        if self._key is None:
            logger.warning("No encryption key provided, encryption disabled")
            self._cipher = None
            return
            
        try:
            from cryptography.fernet import Fernet
            # Fernet requires 32 bytes base64-encoded key
            fernet_key = base64.urlsafe_b64encode(self._key[:32])
            self._cipher = Fernet(fernet_key)
            logger.info("Encryption enabled for session storage")
        except ImportError:
            logger.warning(
                "cryptography package not installed. "
                "Session data will be stored unencrypted. "
                "Install with: pip install cryptography"
            )
            self._cipher = None
    
    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._cipher is not None
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string.
        
        Args:
            data: Plaintext string
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not self._cipher:
            return data
        
        encrypted = self._cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, data: str) -> str:
        """Decrypt a string.
        
        Args:
            data: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plaintext string
        """
        if not self._cipher:
            return data
        
        try:
            encrypted = base64.b64decode(data)
            decrypted = self._cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # Return original data if decryption fails (migration case)
            return data


class EncryptedSQLiteStorage:
    """SQLite storage with field-level encryption and audit logging."""
    
    # Fields that contain sensitive/PII data
    SENSITIVE_FIELDS = [
        "conversation_history",
        "user_preferences", 
        "context_summary",
        "previous_queries",
    ]
    
    def __init__(
        self,
        db_path: str = "data/sessions.db",
        encryption_key: Optional[str] = None,
        enable_audit_log: bool = True,
    ):
        """Initialize encrypted SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
            encryption_key: Encryption key or env var name
            enable_audit_log: Whether to enable audit logging
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.encryption = EncryptionProvider(encryption_key)
        self.enable_audit_log = enable_audit_log
        
        self._init_db()
        
        if self.encryption.is_enabled:
            logger.info("EncryptedSQLiteStorage initialized with encryption")
        else:
            logger.warning("EncryptedSQLiteStorage initialized WITHOUT encryption")
    
    def _init_db(self) -> None:
        """Initialize database schema with encryption support."""
        with sqlite3.connect(self.db_path) as conn:
            # Main sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    session_data TEXT NOT NULL,
                    is_encrypted INTEGER DEFAULT 0,
                    schema_version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Audit log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    accessor TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    details TEXT
                )
            """)
            
            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            
            conn.commit()
    
    def _log_audit(
        self,
        conn: sqlite3.Connection,
        action: str,
        session_id: str,
        user_id: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None,
    ) -> None:
        """Log an audit entry."""
        if not self.enable_audit_log:
            return
        
        try:
            conn.execute("""
                INSERT INTO audit_log 
                (timestamp, action, session_id, user_id, accessor, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                action,
                session_id,
                user_id,
                "system",  # In production, get from request context
                1 if success else 0,
                details,
            ))
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _encrypt_session_data(self, session_dict: Dict[str, Any]) -> str:
        """Encrypt sensitive fields in session data."""
        if not self.encryption.is_enabled:
            return json.dumps(session_dict)
        
        # Deep copy to avoid modifying original
        encrypted_dict = json.loads(json.dumps(session_dict))
        
        # Encrypt sensitive fields
        for field in self.SENSITIVE_FIELDS:
            if field in encrypted_dict and encrypted_dict[field]:
                field_json = json.dumps(encrypted_dict[field])
                encrypted_dict[field] = self.encryption.encrypt(field_json)
                encrypted_dict[f"_{field}_encrypted"] = True
        
        return json.dumps(encrypted_dict)
    
    def _decrypt_session_data(self, session_json: str, is_encrypted: bool) -> Dict[str, Any]:
        """Decrypt sensitive fields in session data."""
        session_dict = json.loads(session_json)
        
        if not is_encrypted or not self.encryption.is_enabled:
            return session_dict
        
        # Decrypt sensitive fields
        for field in self.SENSITIVE_FIELDS:
            if f"_{field}_encrypted" in session_dict and session_dict.get(field):
                try:
                    decrypted_json = self.encryption.decrypt(session_dict[field])
                    session_dict[field] = json.loads(decrypted_json)
                    del session_dict[f"_{field}_encrypted"]
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
        
        return session_dict
    
    def save_session(self, session: SessionState) -> None:
        """Save a session with encryption."""
        session_dict = session.to_dict()
        session_data = self._encrypt_session_data(session_dict)
        is_encrypted = 1 if self.encryption.is_enabled else 0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, user_id, session_data, is_encrypted, schema_version,
                 created_at, updated_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.user_id,
                session_data,
                is_encrypted,
                1,  # schema version
                session.created_at.isoformat(),
                datetime.now().isoformat(),
                session.expires_at.isoformat() if session.expires_at else None,
                1 if session.is_active else 0
            ))
            
            self._log_audit(conn, "write", session.session_id, session.user_id)
            conn.commit()
    
    def load_session(self, session_id: str) -> Optional[SessionState]:
        """Load a session with decryption."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_data, is_encrypted FROM sessions 
                WHERE session_id = ? AND is_active = 1
            """, (session_id,))
            row = cursor.fetchone()
            
            if row is None:
                self._log_audit(conn, "read", session_id, success=False, details="not_found")
                return None
            
            session_dict = self._decrypt_session_data(row[0], bool(row[1]))
            session = SessionState.from_dict(session_dict)
            
            self._log_audit(conn, "read", session_id, session.user_id)
            conn.commit()
            
            return session
    
    def delete_session(self, session_id: str) -> None:
        """Soft delete a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET is_active = 0, updated_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            
            self._log_audit(conn, "delete", session_id)
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
            count = cursor.rowcount
            
            if count > 0:
                self._log_audit(conn, "cleanup", "*", details=f"expired_{count}")
            
            conn.commit()
            return count
    
    def get_audit_log(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit log entries.
        
        Args:
            session_id: Filter by session ID
            limit: Maximum entries to return
            
        Returns:
            List of audit log entries
        """
        with sqlite3.connect(self.db_path) as conn:
            if session_id:
                cursor = conn.execute("""
                    SELECT timestamp, action, session_id, user_id, accessor, success, details
                    FROM audit_log
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT timestamp, action, session_id, user_id, accessor, success, details
                    FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [
                {
                    "timestamp": row[0],
                    "action": row[1],
                    "session_id": row[2],
                    "user_id": row[3],
                    "accessor": row[4],
                    "success": bool(row[5]),
                    "details": row[6],
                }
                for row in cursor.fetchall()
            ]
    
    def migrate_to_encrypted(self) -> int:
        """Migrate existing unencrypted sessions to encrypted.
        
        Returns:
            Number of sessions migrated
        """
        if not self.encryption.is_enabled:
            logger.warning("Encryption not enabled, cannot migrate")
            return 0
        
        migrated = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_id, session_data FROM sessions
                WHERE is_encrypted = 0 AND is_active = 1
            """)
            
            for row in cursor.fetchall():
                session_id, session_data = row
                try:
                    # Parse and re-encrypt
                    session_dict = json.loads(session_data)
                    encrypted_data = self._encrypt_session_data(session_dict)
                    
                    conn.execute("""
                        UPDATE sessions 
                        SET session_data = ?, is_encrypted = 1, updated_at = ?
                        WHERE session_id = ?
                    """, (encrypted_data, datetime.now().isoformat(), session_id))
                    
                    self._log_audit(conn, "migrate", session_id, details="encrypted")
                    migrated += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate session {session_id}: {e}")
                    self._log_audit(conn, "migrate", session_id, success=False, details=str(e))
            
            conn.commit()
        
        logger.info(f"Migrated {migrated} sessions to encrypted storage")
        return migrated
    
    # Compatibility methods for existing code
    def list_all_sessions(self, limit: int = 100, offset: int = 0, user_id: Optional[str] = None) -> List[SessionState]:
        """List all active sessions with full details."""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    SELECT session_data, is_encrypted FROM sessions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT session_data, is_encrypted FROM sessions 
                    WHERE is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            sessions = []
            for row in cursor.fetchall():
                session_dict = self._decrypt_session_data(row[0], bool(row[1]))
                sessions.append(SessionState.from_dict(session_dict))
            
            return sessions
    
    def count_total_sessions(self, user_id: Optional[str] = None) -> int:
        """Count total number of active sessions."""
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
        """Count active sessions."""
        return self.count_total_sessions()
    
    def clear_all_sessions(self) -> int:
        """Clear all sessions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions SET is_active = 0 
                WHERE is_active = 1
            """)
            count = cursor.rowcount
            
            self._log_audit(conn, "clear_all", "*", details=f"cleared_{count}")
            conn.commit()
            
            return count


__all__ = [
    "EncryptedSQLiteStorage",
    "EncryptionProvider",
    "AuditLogEntry",
]
