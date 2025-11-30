
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel, Field

from ai_server.api.dependencies import get_session_manager
from ai_server.memory.session_manager import SessionManager
from ai_server.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID")

@router.post("")
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    session = session_manager.create_session(user_id=request.user_id)
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat()
    }

@router.get("")
async def get_sessions(
    limit: int = 100, 
    offset: int = 0, 
    user_id: Optional[str] = None,
    session_manager: SessionManager = Depends(get_session_manager)
):
    sessions = session_manager.storage.list_all_sessions(limit=limit, offset=offset, user_id=user_id)
    
    # Filter out empty sessions (no queries)
    active_sessions = []
    for s in sessions:
        query_count = len(s.conversation_history.turns)
        if query_count > 0:
            active_sessions.append({
                "session_id": s.session_id,
                "user_id": s.user_id,
                "created_at": s.created_at.isoformat(),
                "query_count": query_count,
                # Add first query as title if available
                "queries": [t.user_query for t in s.conversation_history.turns]
            })
            
    return {
        "total_sessions": len(active_sessions),
        "sessions": active_sessions
    }

@router.get("/{session_id}")
async def get_session_detail(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "session_id": session.session_id,
        "conversation_history": [t.to_dict() for t in session.conversation_history.turns],
        "user_preferences": session.user_preferences.dict()
    }

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    session_manager.delete_session(session_id)
    return {"message": "Session deleted"}

@router.post("/clear")
async def clear_all_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Clear all sessions"""
    count = session_manager.storage.clear_all_sessions()
    return {"message": f"Cleared {count} sessions"}
