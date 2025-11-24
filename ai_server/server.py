"""
FastAPI Server for Amazon Smart Shopping Assistant
Provides REST API endpoints for the AI shopping agent
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json
import time
from contextlib import asynccontextmanager

from ai_server.graphs.shopping_graph import build_graph
from ai_server.core.config import load_config, get_config_value
from ai_server.core.telemetry import configure_langsmith
from ai_server.memory.session_manager import SessionManager
from ai_server.memory.conversation_memory import ConversationMemory
from ai_server.utils.logger import (
    get_logger,
    get_request_logger,
    get_error_logger,
    log_request,
    log_response,
    log_error,
)

# Initialize loggers
logger = get_logger(__name__)
request_logger = get_request_logger()
error_logger = get_error_logger()

# Initialize SessionManager with SQLite storage
session_manager: Optional[SessionManager] = None

# Store token usage and graph traces (kept in memory for analytics)
token_usage: Dict[str, Dict[str, Any]] = {}
graph_traces: Dict[str, List[Dict[str, Any]]] = {}  # Store graph execution traces


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global session_manager
    
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting AI Server...")
    load_config()
    configure_langsmith()
    
    # Initialize SessionManager
    db_path = get_config_value("memory.storage.sqlite.db_path", "data/sessions.db")
    session_manager = SessionManager()
    logger.info(f"📦 SessionManager initialized with SQLite: {db_path}")
    
    logger.info("✅ AI Server ready!")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 Shutting down AI Server...")
    if session_manager:
        # Get session stats
        try:
            active_sessions = session_manager.storage.count_active_sessions()
            logger.info(f"Total active sessions: {active_sessions}")
        except:
            pass
    logger.info(f"Total graph traces: {sum(len(v) for v in graph_traces.values())}")
    logger.info("=" * 80)


app = FastAPI(
    title="Amazon Smart Shopping Assistant API",
    description="AI-powered shopping assistant with 4 autonomous agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request Logging Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses"""
    start_time = time.time()
    
    # Log request
    log_request(
        request_logger,
        request.method,
        request.url.path,
        session_id=request.query_params.get("session_id")
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        duration_ms = (time.time() - start_time) * 1000
        log_response(
            request_logger,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            session_id=request.query_params.get("session_id")
        )
        
        return response
    except Exception as e:
        # Log error
        duration_ms = (time.time() - start_time) * 1000
        log_error(error_logger, e, f"Request failed: {request.method} {request.url.path}")
        log_response(
            request_logger,
            request.method,
            request.url.path,
            500,
            duration_ms,
            session_id=request.query_params.get("session_id")
        )
        raise


# ============================================================================
# Request/Response Models
# ============================================================================

class ShoppingRequest(BaseModel):
    query: str = Field(..., description="User's shopping query")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class ProductInfo(BaseModel):
    title: str
    link: str
    price: str
    rating: Optional[float] = None
    reviews: Optional[int] = None
    image: Optional[str] = None
    position: Optional[int] = None
    source: Optional[str] = None
    delivery: Optional[str] = None
    thumbnail: Optional[str] = None


class RecommendationInfo(BaseModel):
    recommended_product: ProductInfo
    value_score: float
    reasoning: str
    explanation: str
    tradeoff_analysis: Optional[str] = None


class ShoppingResponse(BaseModel):
    session_id: str
    user_query: str
    matched_products: List[ProductInfo]
    recommendation: RecommendationInfo
    alternatives: Optional[List[ProductInfo]] = None
    total_results: int
    search_metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


# ============================================================================
# Shopping Endpoints
# ============================================================================

@app.post("/api/shopping", response_model=ShoppingResponse)
async def search_products(request: ShoppingRequest):
    """
    Main shopping search endpoint
    Returns product recommendations with AI analysis
    """
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    # Get or create session
    session = session_manager.get_or_create_session(
        session_id=request.session_id,
        user_id=request.user_preferences.get("user_id") if request.user_preferences else None
    )
    session_id = session.session_id
    
    logger.info(
        f"Shopping search started",
        extra={
            "session_id": session_id,
            "query": request.query,
            "has_preferences": session.user_preferences.confidence > 0
        }
    )
    
    try:
        # Build and run graph
        graph = build_graph()
        
        # Prepare initial state with session context
        initial_state = {
            "user_query": request.query,
            "session_id": session_id,
            "user_preferences": session.user_preferences,
            "previous_queries": session.conversation_history.get_recent_queries(5),
        }
        
        # Run graph
        logger.debug(f"Running graph for session {session_id}")
        result = await asyncio.to_thread(
            graph.invoke,
            initial_state
        )
        
        # Extract products from result
        matched_products = result.get("matched_products", [])
        recommendation = result.get("recommendation", {})
        
        logger.info(
            f"Search completed",
            extra={
                "session_id": session_id,
                "total_results": len(matched_products),
                "has_recommendation": bool(recommendation)
            }
        )
        
    except Exception as e:
        log_error(
            error_logger,
            e,
            f"Error in search_products for session {session_id}",
            session_id=session_id,
            query=request.query
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process shopping request: {str(e)}"
        )
    
    try:
        # Convert to response format
        products = [
            ProductInfo(
                title=p.get("title", ""),
                link=p.get("link", ""),
                price=p.get("price", ""),
                rating=p.get("rating"),
                reviews=p.get("reviews"),
                image=p.get("image"),
                position=p.get("position"),
                source=p.get("source"),
                delivery=p.get("delivery"),
                thumbnail=p.get("thumbnail"),
            )
            for p in matched_products[:10]  # Limit to top 10
        ]
        
        # Get recommended product
        rec_product = recommendation.get("product", {})
        if rec_product:
            rec_info = RecommendationInfo(
                recommended_product=ProductInfo(
                    title=rec_product.get("title", ""),
                    link=rec_product.get("link", ""),
                    price=rec_product.get("price", ""),
                    rating=rec_product.get("rating"),
                    reviews=rec_product.get("reviews"),
                    image=rec_product.get("image"),
                ),
                value_score=recommendation.get("value_score", 0.0),
                reasoning=recommendation.get("reasoning", ""),
                explanation=recommendation.get("explanation", ""),
                tradeoff_analysis=recommendation.get("tradeoff_analysis"),
            )
        else:
            # Fallback if no specific recommendation
            rec_info = RecommendationInfo(
                recommended_product=products[0] if products else ProductInfo(
                    title="No products found",
                    link="",
                    price="$0.00"
                ),
                value_score=0.5,
                reasoning="No specific recommendation available",
                explanation="Please try a different search query",
            )
        
        response = ShoppingResponse(
            session_id=session_id,
            user_query=request.query,
            matched_products=products,
            recommendation=rec_info,
            alternatives=products[1:4] if len(products) > 1 else None,
            total_results=len(matched_products),
            search_metadata=result.get("metadata", {}),
        )
        
        # Update session with conversation turn
        top_recommendation = rec_info.recommended_product.title if rec_info else None
        ConversationMemory.add_turn_to_session(
            session,
            user_query=request.query,
            search_plan=result.get("search_plan"),
            products_found=len(matched_products),
            top_recommendation=top_recommendation,
        )
        
        # Save session
        session_manager.update_session(session)
        logger.info(f"Session updated: {session_id}, total turns: {len(session.conversation_history.turns)}")
        
        # Store graph trace for debugging
        if session_id not in graph_traces:
            graph_traces[session_id] = []
        
        graph_traces[session_id].append({
            "timestamp": datetime.now().isoformat(),
            "node": "search_products",
            "inputs": {"query": request.query},
            "outputs": {
                "total_results": len(matched_products),
                "has_recommendation": bool(recommendation),
            },
            "duration_ms": None,  # Can add timing if needed
        })
        
        logger.debug(
            f"Graph trace stored",
            extra={
                "session_id": session_id,
                "total_traces": len(graph_traces[session_id])
            }
        )
        
        return response
        
    except Exception as e:
        log_error(
            error_logger,
            e,
            f"Failed to format search response for session {session_id}",
            session_id=session_id
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/shopping/stream")
async def search_products_stream(request: ShoppingRequest):
    """
    Streaming search endpoint with Server-Sent Events (SSE)
    Provides real-time updates as the AI processes the search
    """
    session_id = request.session_id or f"session_{datetime.now().timestamp()}"
    
    logger.info(
        f"Streaming search started",
        extra={
            "session_id": session_id,
            "query": request.query
        }
    )
    
    async def event_generator():
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            logger.debug(f"Streaming: sent start event for {session_id}")
            
            # Build graph
            graph = build_graph()
            
            # Prepare initial state
            initial_state = {
                "user_query": request.query,
                "session_id": session_id,
            }
            
            # Stream events from graph
            step_count = 0
            async for event in graph.astream_events(initial_state, version="v2"):
                step_count += 1
                
                # Send progress events
                if event.get("event") == "on_chain_start":
                    yield f"data: {json.dumps({'type': 'progress', 'step': step_count, 'message': 'Processing...'})}\n\n"
                
                # Send chunk events for LLM streaming
                if event.get("event") == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", {})
                    if chunk:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': str(chunk)})}\n\n"
            
            # Get final result
            result = await asyncio.to_thread(graph.invoke, initial_state)
            
            # Send completion event with result
            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"
            
            logger.info(
                f"Streaming search completed",
                extra={
                    "session_id": session_id,
                    "total_steps": step_count
                }
            )
            
        except Exception as e:
            log_error(
                error_logger,
                e,
                f"Streaming search failed for session {session_id}",
                session_id=session_id,
                query=request.query
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Session Management
# ============================================================================

class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID for session tracking")


@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest):
    """Create a new session with memory and personalization"""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    user_id = request.user_id
    session = session_manager.create_session(user_id=user_id)
    session_id = session.session_id
    
    logger.info(
        f"Session created",
        extra={
            "session_id": session_id,
            "user_id": user_id
        }
    )
    
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat() if session.expires_at else None
    }


@app.get("/api/sessions")
async def get_sessions(limit: int = 100, offset: int = 0, user_id: Optional[str] = None):
    """List all sessions with pagination"""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    logger.debug(f"Listing sessions: limit={limit}, offset={offset}, user_id={user_id}")
    
    try:
        # Get sessions from storage
        sessions = session_manager.storage.list_all_sessions(limit=limit, offset=offset, user_id=user_id)
        total_count = session_manager.storage.count_total_sessions(user_id=user_id)
        
        # Convert to response format
        sessions_data = []
        for session in sessions:
            # Extract queries from conversation history
            queries = session.conversation_history.get_recent_queries(10)
            
            # Extract learned preferences
            learned_prefs = []
            if session.user_preferences.liked_brands:
                learned_prefs.extend(session.user_preferences.liked_brands[:3])
            if session.user_preferences.must_have_features:
                learned_prefs.extend(session.user_preferences.must_have_features[:3])
            if session.user_preferences.max_budget:
                learned_prefs.append(f"Budget: ${session.user_preferences.max_budget}")
            
            sessions_data.append({
                "session_id": session.session_id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.conversation_history.updated_at.isoformat(),
                "queries": queries,
                "query_count": len(session.conversation_history.turns),
                "learned_preferences": learned_prefs[:5],  # Limit to 5
                "is_active": session.is_active,
            })
        
        logger.info(f"Returned {len(sessions_data)} sessions (total: {total_count})")
        
        return {
            "total_sessions": total_count,
            "sessions": sessions_data,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        log_error(error_logger, e, "Failed to list sessions")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """Get session details including conversation history and preferences"""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    logger.debug(f"Retrieving session details: {session_id}")
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "conversation_history": [t.to_dict() for t in session.conversation_history.turns],
        "user_preferences": {
            "confidence": session.user_preferences.confidence,
            "liked_brands": session.user_preferences.liked_brands,
            "must_have_features": session.user_preferences.must_have_features,
            "preferred_price_range": session.user_preferences.preferred_price_range,
            "max_budget": session.user_preferences.max_budget,
        },
        "is_active": session.is_active,
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    session_manager.delete_session(session_id)
    logger.info(f"Session deleted: {session_id}")
    
    return {"message": f"Session {session_id} deleted"}


@app.post("/api/sessions/clear")
async def clear_all_sessions():
    """Clear all sessions (use with caution!)"""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    # Note: This requires implementing clear_all in storage
    logger.warning("Clear all sessions requested - not implemented")
    return {"message": "Clear all sessions not yet implemented"}


# ============================================================================
# Monitoring & Debug
# ============================================================================

@app.get("/api/monitoring/token-usage")
async def get_global_token_stats():
    """Get global token usage statistics"""
    logger.debug("Retrieving global token usage statistics")
    return {
        "total_usage": {
            "total_tokens": sum(s.get("total_tokens", 0) for s in token_usage.values()),
            "prompt_tokens": sum(s.get("prompt_tokens", 0) for s in token_usage.values()),
            "completion_tokens": sum(s.get("completion_tokens", 0) for s in token_usage.values()),
        },
        "by_session": token_usage,
    }


@app.get("/api/monitoring/token-usage/{session_id}")
async def get_session_token_stats(session_id: str):
    """Get token usage for specific session"""
    logger.debug(f"Retrieving token usage for session: {session_id}")
    if session_id not in token_usage:
        return {
            "session_id": session_id,
            "total_usage": {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        }
    
    return {
        "session_id": session_id,
        "total_usage": token_usage[session_id],
    }


@app.post("/api/monitoring/token-usage/reset")
async def reset_token_stats():
    """Reset token usage statistics"""
    count = len(token_usage)
    token_usage.clear()
    logger.info(f"Token usage statistics reset (cleared {count} sessions)")
    return {"message": "Token usage statistics reset"}


@app.get("/api/debug/graph-traces/{session_id}")
async def get_graph_traces(session_id: str):
    """
    Get graph execution traces for debugging
    Returns detailed execution logs for a specific session
    """
    logger.debug(f"Retrieving graph traces for session: {session_id}")
    
    if session_id not in graph_traces:
        logger.warning(f"No graph traces found for session: {session_id}")
        return {
            "session_id": session_id,
            "traces": [],
            "total_traces": 0,
        }
    
    return {
        "session_id": session_id,
        "traces": graph_traces[session_id],
        "total_traces": len(graph_traces[session_id]),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
