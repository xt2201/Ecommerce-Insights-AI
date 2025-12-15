"""
FastAPI Server for 100% Agentic Shopping Assistant
"""
import uuid
import logging
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from ai_server.graphs.shopping_graph import build_graph, GraphState
from ai_server.schemas.session_memory import SessionMemory
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory session storage for demo
# In production, this should use Redis or SQLite
sessions: Dict[str, SessionMemory] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Agentic AI Server...")
    yield
    logger.info("🛑 Shutting down Agentic AI Server...")

app = FastAPI(
    title="XT AI Shopping Assistant (Agentic)",
    version="5.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestData(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_preferences: Optional[Dict] = None

class ProductInfo(BaseModel):
    title: str
    price: str
    rating: Optional[str] = None
    image: Optional[str] = None
    link: Optional[str] = None

class ResponseData(BaseModel):
    session_id: str
    user_query: str
    final_answer: str
    matched_products: List[Dict[str, Any]] = []
    metadata: Optional[Dict] = None

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0", "mode": "agentic"}

@app.post("/api/shopping", response_model=ResponseData)
async def chat(request: RequestData):
    session_id = request.session_id or str(uuid.uuid4())
    
    # Retrieve or create session memory
    if session_id in sessions:
        memory = sessions[session_id]
        logger.info(f"Resuming session: {session_id}")
    else:
        memory = SessionMemory(session_id=session_id)
        sessions[session_id] = memory
        logger.info(f"Created new session: {session_id}")
    
    # Build graph
    graph = build_graph()
    
    # Run graph
    inputs: GraphState = {
        "user_message": request.query,
        "session_id": session_id,
        "memory": memory
    }
    
    try:
        result = graph.invoke(inputs)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    # Update memory
    updated_memory = result.get("memory")
    if updated_memory:
        sessions[session_id] = updated_memory
    
    # Format response for frontend
    # The frontend expects 'matched_products' to display cards
    candidates = result.get("candidates", [])
    products = []
    
    for c in candidates:
        # Check if 'c' is an object or dict
        if isinstance(c, dict):
            p_data = c
        else:
            p_data = c.__dict__
            
        products.append({
            "title": p_data.get("title", "Unknown"),
            "price": str(p_data.get("price", "")),
            "rating": str(p_data.get("rating", "")),
            "image": p_data.get("thumbnail") or p_data.get("image", ""),
            "link": p_data.get("link", "#"),
            "source": p_data.get("source", "amazon")
        })
        
    final_response = result.get("final_response", "Sorry, I encountered an error.")
    
    return ResponseData(
        session_id=session_id,
        user_query=request.query,
        final_answer=final_response,
        matched_products=products,
        metadata={"route": result.get("route")}
    )

# Streaming endpoint (simple compatibility)
@app.post("/api/shopping/stream")
async def chat_stream(request: RequestData):
    # For now, just forward to standard chat but wrap in SSE format if possible
    # Or just return JSON and let frontend handle it (frontend might expect SSE)
    # To properly support SSE, we need a generator.
    # For the agentic demo, we'll implement simple SSE wrapping the final response
    # effectively confusing the frontend but making it work, OR we accept that
    # the frontend might need a tweak.
    # Actually, let's implement true SSE with intermediate steps if possible, 
    # but for now, let's just create a non-streaming response that looks like a completed stream.
    
    # NOTE: The frontend likely fails if this doesn't return SSE.
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    async def event_generator():
        # Ensure session_id exists
        session_id = request.session_id or str(uuid.uuid4())
        # Update request object with session_id so chat() uses it
        request.session_id = session_id
        
        # Start
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
        
        # Process (blocking call inside async generator is bad, but for demo ok)
        # Better: run in threadpool
        response_data = await chat(request)

        
        # Progress
        yield f"data: {json.dumps({'type': 'progress', 'step': 1, 'node': 'Agentic Brain', 'message': 'Thinking...'})}\n\n"
        
        # Result
        result_dict = response_data.dict()
        # Ensure matched_products is top level/correctly formatted
        # Frontend expects: 'recommendation' object usually
        
        # Mock recommendation object for compatibility
        if result_dict['matched_products']:
            top = result_dict['matched_products'][0]
            rec_info = {
                "recommended_product": top,
                "value_score": 0.95,
                "reasoning": "Best match",
                "explanation": "Agentic choice"
            }
        else:
            rec_info = None
            
        full_result = {
            "session_id": result_dict['session_id'],
            "user_query": result_dict['user_query'],
            "matched_products": result_dict['matched_products'],
            "recommendation": rec_info,
            "final_answer": result_dict['final_answer'],
            "total_results": len(result_dict['matched_products'])
        }
        
        yield f"data: {json.dumps({'type': 'complete', 'result': full_result})}\n\n"
        yield "data: {\"type\": \"end\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
# ============================================================================
# Session Management Endpoints
# ============================================================================

class SessionInfo(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    created_at: str
    updated_at: str
    queries: List[str]
    query_count: int
    learned_preferences: List[str]
    is_active: bool

class SessionsResponse(BaseModel):
    total_sessions: int
    sessions: List[SessionInfo]

@app.post("/api/sessions")
async def create_session(request: Dict[str, Any]):
    user_id = request.get("user_id")
    session_id = str(uuid.uuid4())
    memory = SessionMemory(session_id=session_id)
    sessions[session_id] = memory
    logger.info(f"Created new session via API: {session_id}")
    return {"session_id": session_id}

@app.get("/api/sessions", response_model=SessionsResponse)
async def get_sessions(limit: int = 100, offset: int = 0):
    # Sort sessions by updated_at (approx logic)
    # Using sessions.values()
    session_list = []
    from datetime import datetime
    
    for s_id, mem in sessions.items():
        # Check if memory has timestamp fields, otherwise mock
        created = getattr(mem, "created_at", datetime.now().isoformat())
        updated = getattr(mem, "last_updated", datetime.now().isoformat())
        
        # Extract queries from chat history
        queries = [t.content for t in mem.turns if t.role == "user"]
        
        session_list.append(SessionInfo(
            session_id=s_id,
            user_id=mem.user_id or "user",  # Use mem.user_id
            created_at=str(created),
            updated_at=str(updated),
            queries=queries[:10],
            query_count=len(queries),
            learned_preferences=[], # TODO: Extract from memory if available
            is_active=True
        ))
    
    # Sort by updated_at desc
    session_list.sort(key=lambda x: x.updated_at, reverse=True)
    
    return SessionsResponse(
        total_sessions=len(session_list),
        sessions=session_list[offset:offset+limit]
    )

@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    mem = sessions[session_id]
    
    # Convert chat history to dict format expected by frontend
    history = []
    from datetime import datetime
    
    # Simple conversion of langchain messages to conversation turns
    for turn in mem.turns:
        if turn.role == "user":
            history.append({
                "timestamp": turn.timestamp.isoformat(),
                "user_query": turn.content,
                "products_found": 0, # Cannot easily reconstruct history stats without storing them
                "metadata": {"intent": turn.intent_type}
            })
            
    return {
        "session_id": session_id,
        "created_at": mem.created_at.isoformat(),
        "conversation_history": history,
        "user_preferences": {}
    }

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/api/sessions/clear")
async def clear_all_sessions():
    sessions.clear()
    return {"message": "All sessions cleared"}

# ============================================================================
# Monitoring & Debug Endpoints
# ============================================================================

@app.get("/api/monitoring/token-usage")
async def get_token_usage():
    # Mock data
    return {
        "total_usage": {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        },
        "by_agent": {}
    }

@app.post("/api/monitoring/token-usage/reset")
async def reset_token_usage():
    return {"message": "Stats reset"}

@app.get("/api/debug/graph-traces/{session_id}")
async def get_graph_traces(session_id: str):
    return {
        "session_id": session_id,
        "traces": [],
        "total_traces": 0
    }
