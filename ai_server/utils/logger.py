"""
Professional Logging System for Amazon Smart Shopping Assistant

This module provides a centralized, production-ready logging configuration
with support for:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File rotation to prevent disk space issues
- Structured logging with timestamps and contextual information
- Separate loggers for different components (server, agents, tools, etc.)
- Console and file output with different formats
- Request/response logging with correlation IDs

Usage:
    from ai_server.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Starting operation", extra={"user_id": "123"})
    logger.error("Operation failed", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

# Log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log levels mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Default configuration
DEFAULT_LOG_LEVEL = "INFO"
MAX_FILE_SIZE = 1000 * 1024 * 1024  # 1000 MB
BACKUP_COUNT = 5  # Keep 5 backup files
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"

# ============================================================================
# Formatters
# ============================================================================

# Detailed format for file logs
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(funcName)s:%(lineno)d | %(message)s"
)

# Concise format for console
CONSOLE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

# Date format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# Custom Formatter with Colors (for console)
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds color to console output based on log level
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )
        return super().format(record)

# ============================================================================
# Logger Factory
# ============================================================================

# Store created loggers to avoid duplicates
_loggers = {}
_initialized = False

def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    console_level: str = CONSOLE_LOG_LEVEL,
    file_level: str = FILE_LOG_LEVEL,
) -> None:
    """
    Initialize the root logger configuration.
    This should be called once at application startup.
    
    Args:
        log_level: Default log level for all loggers
        console_level: Log level for console output
        file_level: Log level for file output
    """
    global _initialized
    
    if _initialized:
        return
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(console_level, logging.INFO))
    console_formatter = ColoredFormatter(
        fmt=CONSOLE_FORMAT,
        datefmt=DATE_FORMAT
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler (rotating)
    main_log_file = LOG_DIR / "ai_server.log"
    file_handler = RotatingFileHandler(
        filename=main_log_file,
        maxBytes=MAX_FILE_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(LOG_LEVELS.get(file_level, logging.DEBUG))
    file_formatter = logging.Formatter(
        fmt=DETAILED_FORMAT,
        datefmt=DATE_FORMAT
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    _initialized = True
    
    # Log initialization
    root_logger.info("=" * 80)
    root_logger.info(f"Logging system initialized at {datetime.now()}")
    root_logger.info(f"Log directory: {LOG_DIR}")
    root_logger.info(f"Console level: {console_level}, File level: {file_level}")
    root_logger.info("=" * 80)


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the module)
        log_file: Optional separate log file for this logger
        level: Optional specific log level for this logger
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
        >>> logger.error("Failed to connect", exc_info=True)
    """
    # Ensure logging is initialized
    if not _initialized:
        setup_logging()
    
    # Return existing logger if already created
    if name in _loggers and log_file is None:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    
    # Set specific level if provided
    if level:
        logger.setLevel(LOG_LEVELS.get(level, logging.INFO))
    
    # Add separate file handler if specified
    if log_file:
        log_path = LOG_DIR / log_file
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=MAX_FILE_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt=DETAILED_FORMAT,
            datefmt=DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Cache and return
    _loggers[name] = logger
    return logger


# ============================================================================
# Specialized Loggers
# ============================================================================

def get_request_logger() -> logging.Logger:
    """
    Get logger for HTTP request/response logging
    """
    return get_logger("ai_server.requests", log_file="requests.log")


def get_agent_logger() -> logging.Logger:
    """
    Get logger for agent execution logging
    """
    return get_logger("ai_server.agents", log_file="agents.log")


def get_tool_logger() -> logging.Logger:
    """
    Get logger for tool execution logging
    """
    return get_logger("ai_server.tools", log_file="tools.log")


def get_error_logger() -> logging.Logger:
    """
    Get logger for error tracking
    """
    return get_logger("ai_server.errors", log_file="errors.log", level="ERROR")


# ============================================================================
# Utility Functions
# ============================================================================

def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    session_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log an HTTP request with structured information
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        path: Request path
        session_id: Optional session ID for correlation
        **kwargs: Additional context to log
    """
    extra = {"session_id": session_id, **kwargs} if session_id else kwargs
    logger.info(
        f"Request: {method} {path}",
        extra=extra
    )


def log_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    session_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log an HTTP response with structured information
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        session_id: Optional session ID for correlation
        **kwargs: Additional context to log
    """
    extra = {
        "session_id": session_id,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs
    }
    logger.info(
        f"Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra=extra
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str = "",
    **kwargs
) -> None:
    """
    Log an error with full traceback and context
    
    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional context description
        **kwargs: Additional context to log
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)
    logger.error(
        error_msg,
        exc_info=True,
        extra=kwargs
    )


# ============================================================================
# Initialize on import (with default settings)
# ============================================================================

# Auto-initialize with defaults when module is imported
setup_logging()
