
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ai_server.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory token tracking (should be moved to Redis/DB for production)
_token_usage: Dict[str, Any] = {
    "total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    "by_agent": {},
    "by_session": {}
}

def track_tokens(session_id: str, agent: str, prompt_tokens: int, completion_tokens: int):
    """Track token usage - called from LLM calls"""
    total = prompt_tokens + completion_tokens
    
    # Global total
    _token_usage["total"]["prompt_tokens"] += prompt_tokens
    _token_usage["total"]["completion_tokens"] += completion_tokens
    _token_usage["total"]["total_tokens"] += total
    
    # By agent
    if agent not in _token_usage["by_agent"]:
        _token_usage["by_agent"][agent] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    _token_usage["by_agent"][agent]["prompt_tokens"] += prompt_tokens
    _token_usage["by_agent"][agent]["completion_tokens"] += completion_tokens
    _token_usage["by_agent"][agent]["total_tokens"] += total
    
    # By session
    if session_id not in _token_usage["by_session"]:
        _token_usage["by_session"][session_id] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    _token_usage["by_session"][session_id]["prompt_tokens"] += prompt_tokens
    _token_usage["by_session"][session_id]["completion_tokens"] += completion_tokens
    _token_usage["by_session"][session_id]["total_tokens"] += total

@router.get("/token-usage")
async def get_token_usage():
    """Get global token usage statistics"""
    return {
        "total_usage": _token_usage["total"],
        "by_agent": _token_usage["by_agent"],
        "by_session": _token_usage["by_session"]
    }

@router.get("/token-usage/{session_id}")
async def get_session_token_usage(session_id: str):
    """Get token usage for specific session"""
    session_usage = _token_usage["by_session"].get(session_id)
    if not session_usage:
        return {
            "session_id": session_id,
            "total_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "by_agent": {}
        }
    return {
        "session_id": session_id,
        "total_usage": session_usage,
        "by_agent": {}  # Would need more granular tracking for per-session agent breakdown
    }

@router.post("/token-usage/reset")
async def reset_token_usage():
    """Reset all token usage statistics"""
    global _token_usage
    _token_usage = {
        "total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "by_agent": {},
        "by_session": {}
    }
    return {"message": "Token usage statistics reset"}
