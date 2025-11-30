"""Debug endpoints for graph tracing and diagnostics."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import aiosqlite
from datetime import datetime

from ai_server.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory trace storage (should be moved to persistent storage for production)
_graph_traces: Dict[str, List[Dict[str, Any]]] = {}

def add_trace(session_id: str, node: str, data: Dict[str, Any]):
    """Add a trace entry for graph execution"""
    if session_id not in _graph_traces:
        _graph_traces[session_id] = []
    
    _graph_traces[session_id].append({
        "timestamp": datetime.now().isoformat(),
        "node": node,
        "data": data
    })

@router.get("/graph-traces/{session_id}")
async def get_graph_traces(session_id: str):
    """Get graph execution traces for a session"""
    traces = _graph_traces.get(session_id, [])
    return {
        "session_id": session_id,
        "traces": traces,
        "total_traces": len(traces)
    }

@router.delete("/graph-traces/{session_id}")
async def clear_graph_traces(session_id: str):
    """Clear traces for a session"""
    if session_id in _graph_traces:
        del _graph_traces[session_id]
    return {"message": f"Traces cleared for session {session_id}"}

@router.get("/checkpoints/{session_id}")
async def get_checkpoints(session_id: str):
    """Get LangGraph checkpoints for a session (thread)"""
    try:
        async with aiosqlite.connect("data/checkpoints.db") as conn:
            cursor = await conn.execute(
                "SELECT * FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 10",
                (session_id,)
            )
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            checkpoints = []
            for row in rows:
                checkpoint = dict(zip(columns, row))
                # Convert bytes to string representation for JSON
                for key, value in checkpoint.items():
                    if isinstance(value, bytes):
                        checkpoint[key] = f"<bytes: {len(value)} bytes>"
                checkpoints.append(checkpoint)
            
            return {
                "session_id": session_id,
                "checkpoints": checkpoints,
                "total": len(checkpoints)
            }
    except Exception as e:
        logger.error(f"Failed to get checkpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))
