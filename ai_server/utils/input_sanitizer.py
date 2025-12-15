"""Input sanitization for prompt injection protection.

This module provides security utilities to sanitize user inputs before
they are injected into LLM prompts. It prevents prompt injection attacks
by detecting and escaping malicious patterns.

Security Features:
- Length limiting
- Control character escaping
- Injection pattern detection
- Suspicious input flagging
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat level classification for suspicious inputs."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    original: str
    sanitized: str
    is_suspicious: bool
    threat_level: ThreatLevel
    detected_patterns: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __bool__(self) -> bool:
        """Returns True if input is safe to use."""
        return not self.is_suspicious or self.threat_level in [ThreatLevel.SAFE, ThreatLevel.LOW]


# Injection patterns to detect (case-insensitive)
INJECTION_PATTERNS = [
    # System/Role manipulation
    (r"(?i)\bsystem\s*:", "system_role_injection", ThreatLevel.CRITICAL),
    (r"(?i)\bassistant\s*:", "assistant_role_injection", ThreatLevel.CRITICAL),
    (r"(?i)\buser\s*:", "user_role_injection", ThreatLevel.HIGH),
    (r"(?i)\bhuman\s*:", "human_role_injection", ThreatLevel.HIGH),
    
    # Instruction override attempts
    (r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "instruction_override", ThreatLevel.CRITICAL),
    (r"(?i)forget\s+(all\s+)?(previous|above|prior|your)\s+(instructions?|prompts?|training|rules?)", "instruction_override", ThreatLevel.CRITICAL),
    (r"(?i)disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "instruction_override", ThreatLevel.CRITICAL),
    (r"(?i)new\s+instructions?\s*:", "new_instruction_injection", ThreatLevel.CRITICAL),
    (r"(?i)override\s+(instructions?|rules?|prompts?)", "instruction_override", ThreatLevel.CRITICAL),
    
    # Jailbreak attempts
    (r"(?i)\bDAN\b", "dan_jailbreak", ThreatLevel.HIGH),
    (r"(?i)do\s+anything\s+now", "dan_jailbreak", ThreatLevel.HIGH),
    (r"(?i)jailbreak", "jailbreak_attempt", ThreatLevel.HIGH),
    (r"(?i)bypass\s+(safety|restrictions?|filters?|rules?)", "bypass_attempt", ThreatLevel.HIGH),
    
    # Code/Tool injection
    (r"<tool>", "tool_injection", ThreatLevel.CRITICAL),
    (r"</tool>", "tool_injection", ThreatLevel.CRITICAL),
    (r"<\|.*?\|>", "special_token_injection", ThreatLevel.HIGH),
    (r"\[\[.*?\]\]", "bracket_injection", ThreatLevel.MEDIUM),
    (r"```python\s*\n.*?exec\s*\(", "code_execution_injection", ThreatLevel.CRITICAL),
    (r"```python\s*\n.*?eval\s*\(", "code_execution_injection", ThreatLevel.CRITICAL),
    (r"```python\s*\n.*?import\s+os", "code_execution_injection", ThreatLevel.CRITICAL),
    (r"```python\s*\n.*?subprocess", "code_execution_injection", ThreatLevel.CRITICAL),
    
    # Prompt leaking attempts
    (r"(?i)show\s+(me\s+)?(your|the)\s+(system\s+)?prompt", "prompt_leak_attempt", ThreatLevel.MEDIUM),
    (r"(?i)what\s+(is|are)\s+your\s+(system\s+)?(instructions?|prompts?|rules?)", "prompt_leak_attempt", ThreatLevel.MEDIUM),
    (r"(?i)reveal\s+(your\s+)?(system\s+)?prompt", "prompt_leak_attempt", ThreatLevel.MEDIUM),
    (r"(?i)print\s+(your\s+)?(system\s+)?prompt", "prompt_leak_attempt", ThreatLevel.MEDIUM),
    
    # Delimiter confusion
    (r"---+", "delimiter_confusion", ThreatLevel.LOW),
    (r"===+", "delimiter_confusion", ThreatLevel.LOW),
    (r"\*\*\*+", "delimiter_confusion", ThreatLevel.LOW),
    
    # Base64/encoding attacks
    (r"(?i)base64\s*:", "encoding_attack", ThreatLevel.MEDIUM),
    (r"(?i)decode\s*\(", "encoding_attack", ThreatLevel.MEDIUM),
    
    # Role-play manipulation
    (r"(?i)pretend\s+(you\s+are|to\s+be|you're)\s+a", "roleplay_manipulation", ThreatLevel.MEDIUM),
    (r"(?i)act\s+as\s+(if\s+you\s+are|a|an)", "roleplay_manipulation", ThreatLevel.MEDIUM),
    (r"(?i)you\s+are\s+now\s+a", "roleplay_manipulation", ThreatLevel.MEDIUM),
]

# Characters that should be escaped or removed
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# Maximum input lengths
MAX_QUERY_LENGTH = 2000
MAX_CHAT_HISTORY_LENGTH = 10000
MAX_SINGLE_MESSAGE_LENGTH = 1000


def sanitize_user_input(
    text: str,
    max_length: int = MAX_QUERY_LENGTH,
    escape_markdown: bool = True,
    strict_mode: bool = False,
) -> SanitizationResult:
    """Sanitize user input for safe prompt injection.
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length (truncates if exceeded)
        escape_markdown: Whether to escape markdown-like patterns
        strict_mode: If True, blocks any suspicious input
        
    Returns:
        SanitizationResult with sanitized text and threat assessment
    """
    if not text:
        return SanitizationResult(
            original="",
            sanitized="",
            is_suspicious=False,
            threat_level=ThreatLevel.SAFE,
        )
    
    original = text
    detected_patterns: List[str] = []
    warnings: List[str] = []
    max_threat = ThreatLevel.SAFE
    
    # Step 1: Length check and truncation
    if len(text) > max_length:
        text = text[:max_length]
        warnings.append(f"Input truncated from {len(original)} to {max_length} characters")
    
    # Step 2: Remove control characters
    control_chars_found = CONTROL_CHARS_PATTERN.findall(text)
    if control_chars_found:
        text = CONTROL_CHARS_PATTERN.sub('', text)
        warnings.append(f"Removed {len(control_chars_found)} control characters")
    
    # Step 3: Detect injection patterns
    for pattern, pattern_name, threat_level in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            detected_patterns.append(pattern_name)
            if threat_level.value > max_threat.value:
                max_threat = threat_level
    
    # Step 4: Escape potentially dangerous sequences
    sanitized = text
    
    # Escape backticks (code blocks)
    if escape_markdown:
        # Replace triple backticks with escaped version
        sanitized = re.sub(r'```', '` ` `', sanitized)
        # Escape single backticks only if they look like code injection
        sanitized = re.sub(r'`([^`]*(?:exec|eval|import|subprocess)[^`]*)`', r"'\1'", sanitized)
    
    # Escape role markers by adding zero-width space
    sanitized = re.sub(r'(?i)(system|assistant|user|human)\s*:', r'\1\u200B:', sanitized)
    
    # Escape tool tags
    sanitized = re.sub(r'<(/?)tool>', r'<\1tool\u200B>', sanitized)
    sanitized = re.sub(r'<\|', r'<\u200B|', sanitized)
    sanitized = re.sub(r'\|>', r'|\u200B>', sanitized)
    
    # Step 5: Determine if suspicious
    is_suspicious = len(detected_patterns) > 0
    
    # In strict mode, upgrade threat level
    if strict_mode and is_suspicious:
        if max_threat == ThreatLevel.LOW:
            max_threat = ThreatLevel.MEDIUM
        elif max_threat == ThreatLevel.MEDIUM:
            max_threat = ThreatLevel.HIGH
    
    # Log suspicious inputs (without logging the actual content to avoid log injection)
    if is_suspicious:
        logger.warning(
            f"Suspicious input detected: threat_level={max_threat.value}, "
            f"patterns={detected_patterns}, input_length={len(original)}"
        )
    
    return SanitizationResult(
        original=original,
        sanitized=sanitized,
        is_suspicious=is_suspicious,
        threat_level=max_threat,
        detected_patterns=detected_patterns,
        warnings=warnings,
    )


def sanitize_chat_history(
    history: List[str],
    max_total_length: int = MAX_CHAT_HISTORY_LENGTH,
    max_message_length: int = MAX_SINGLE_MESSAGE_LENGTH,
) -> Tuple[List[str], List[str]]:
    """Sanitize a list of chat history messages.
    
    Args:
        history: List of previous messages
        max_total_length: Maximum total length of all messages
        max_message_length: Maximum length per message
        
    Returns:
        Tuple of (sanitized_messages, warnings)
    """
    if not history:
        return [], []
    
    sanitized_messages: List[str] = []
    all_warnings: List[str] = []
    total_length = 0
    
    for i, message in enumerate(history):
        # Sanitize each message
        result = sanitize_user_input(
            message,
            max_length=max_message_length,
            strict_mode=True,
        )
        
        # Skip high-threat messages
        if result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            all_warnings.append(f"Message {i} blocked due to {result.threat_level.value} threat")
            continue
        
        # Check total length
        if total_length + len(result.sanitized) > max_total_length:
            all_warnings.append(f"Chat history truncated at message {i} due to length limit")
            break
        
        sanitized_messages.append(result.sanitized)
        total_length += len(result.sanitized)
        
        if result.warnings:
            all_warnings.extend([f"Message {i}: {w}" for w in result.warnings])
    
    return sanitized_messages, all_warnings


def is_safe_input(text: str, strict: bool = False) -> bool:
    """Quick check if input is safe to use.
    
    Args:
        text: Input to check
        strict: If True, blocks even low-threat patterns
        
    Returns:
        True if input is safe
    """
    result = sanitize_user_input(text, strict_mode=strict)
    
    if strict:
        return result.threat_level == ThreatLevel.SAFE
    else:
        return result.threat_level in [ThreatLevel.SAFE, ThreatLevel.LOW]


def create_safe_prompt_context(
    query: str,
    chat_history: Optional[List[str]] = None,
) -> Tuple[str, List[str], dict]:
    """Create safe context for prompt injection.
    
    Args:
        query: User query
        chat_history: Optional chat history
        
    Returns:
        Tuple of (safe_query, safe_history, metadata)
    """
    # Sanitize query
    query_result = sanitize_user_input(query, strict_mode=True)
    
    # Sanitize history
    safe_history = []
    history_warnings = []
    if chat_history:
        safe_history, history_warnings = sanitize_chat_history(chat_history)
    
    metadata = {
        "query_threat_level": query_result.threat_level.value,
        "query_is_suspicious": query_result.is_suspicious,
        "query_patterns_detected": query_result.detected_patterns,
        "history_message_count": len(safe_history),
        "warnings": query_result.warnings + history_warnings,
    }
    
    # Block critical threats
    if query_result.threat_level == ThreatLevel.CRITICAL:
        raise PromptInjectionError(
            f"Input blocked due to critical security threat: {query_result.detected_patterns}"
        )
    
    return query_result.sanitized, safe_history, metadata


class PromptInjectionError(Exception):
    """Raised when a prompt injection attack is detected."""
    pass


__all__ = [
    "sanitize_user_input",
    "sanitize_chat_history",
    "is_safe_input",
    "create_safe_prompt_context",
    "SanitizationResult",
    "ThreatLevel",
    "PromptInjectionError",
    "MAX_QUERY_LENGTH",
    "MAX_CHAT_HISTORY_LENGTH",
]
