
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import asyncio
from datetime import datetime
import uuid
import aiosqlite

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

# Monkeypatch JsonPlusSerializer to add dumps/loads aliases (Fix for langgraph bug)
if not hasattr(JsonPlusSerializer, "dumps"):
    def dumps_wrapper(self, obj):
        type_, data = self.dumps_typed(obj)
        return data
    JsonPlusSerializer.dumps = dumps_wrapper

if not hasattr(JsonPlusSerializer, "loads"):
    def loads_wrapper(self, data):
        return self.loads_typed(('msgpack', data))
    JsonPlusSerializer.loads = loads_wrapper

from ai_server.graphs.shopping_graph import build_graph
from ai_server.api.dependencies import get_session_manager
from ai_server.memory.session_manager import SessionManager
from ai_server.memory.conversation_memory import ConversationMemory
from ai_server.utils.logger import get_logger, get_error_logger, log_error

router = APIRouter()
logger = get_logger(__name__)
error_logger = get_error_logger()

# Request Models
class ShoppingRequest(BaseModel):
    query: str = Field(..., description="User's shopping query")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

class ResumeRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    thread_id: str = Field(..., description="Thread ID from interrupt event")
    user_input: str = Field(..., description="User's answer to clarification")

# Response Models (Simplified for brevity, full models in schemas if needed)
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
    red_flags: Optional[List[str]] = None
    follow_up_suggestions: Optional[List[str]] = None

# Helper to format response
def format_shopping_response(session_id, query, result):
    # Extract products from state (was 'matched_products', now 'products')
    matched_products = result.get("products", [])
    
    # Extract recommendation info
    # Try to get from final_response first (Phase 2)
    final_response = result.get("final_response", {})
    analysis_result = result.get("analysis_result", {})
    
    products = []
    for p in matched_products[:10]:
        products.append(ProductInfo(
            title=p.get("title", ""),
            link=p.get("link", ""),
            price=f"${p.get('price', 0):.2f}" if p.get("price") is not None else "N/A",
            rating=p.get("rating"),
            reviews=p.get("reviews_count") or p.get("reviews"),
            image=p.get("image") or p.get("thumbnail"),
            position=p.get("position"),
            source=p.get("source"),
            delivery=p.get("delivery"),
            thumbnail=p.get("thumbnail"),
        ))
    
    # Construct recommendation info
    rec_info = None
    
    if final_response:
        # Use structured final response
        recs = final_response.get("recommendations", [])
        if recs:
            top_rec = recs[0]
            # Format tradeoff analysis
            tradeoff_raw = final_response.get("reasoning_summary", {}).get("tradeoffs", "")
            tradeoff_str = ""
            if isinstance(tradeoff_raw, dict):
                for k, v in tradeoff_raw.items():
                    tradeoff_str += f"• {k.replace('_', ' ').title()}: {v}\n"
            elif isinstance(tradeoff_raw, list):
                for item in tradeoff_raw:
                    tradeoff_str += f"• {item}\n"
            else:
                tradeoff_str = str(tradeoff_raw)

            rec_info = RecommendationInfo(
                recommended_product=ProductInfo(
                    title=top_rec.get("product_name", ""),
                    link=top_rec.get("purchase_link", ""),
                    price=f"${top_rec.get('price', 0):.2f}" if top_rec.get("price") is not None else "N/A",
                    rating=top_rec.get("rating"),
                ),
                value_score=top_rec.get("value_score", 0.0),
                reasoning=top_rec.get("why_recommended", ""),
                explanation=final_response.get("executive_summary", {}).get("key_reason", ""),
                tradeoff_analysis=tradeoff_str
            )
    
    if not rec_info and analysis_result:
        # Fallback to analysis result
        top_rec_expl = analysis_result.get("top_recommendation", {})
        # We need to find the product object for the top recommendation
        # This is a bit tricky as analysis_result might not have the full product details in top_recommendation
        # But we can try to match with products list
        
        # Format tradeoff analysis
        tradeoff_raw = analysis_result.get("tradeoff_analysis", "")
        tradeoff_str = ""
        if isinstance(tradeoff_raw, dict):
            # Convert dict to bullet points
            for k, v in tradeoff_raw.items():
                tradeoff_str += f"• {k.replace('_', ' ').title()}: {v}\n"
        else:
            tradeoff_str = str(tradeoff_raw)

        rec_info = RecommendationInfo(
            recommended_product=products[0] if products else ProductInfo(title="Analysis complete", link="", price=""),
            value_score=top_rec_expl.get("match_quality", 0.5),
            reasoning=top_rec_expl.get("why_recommended", "Best match"),
            explanation=str(top_rec_expl.get("satisfied_needs", [])),
            tradeoff_analysis=tradeoff_str
        )

    if not rec_info:
        rec_info = RecommendationInfo(
            recommended_product=products[0] if products else ProductInfo(title="No products found", link="", price="$0.00"),
            value_score=0.5,
            reasoning="No specific recommendation available",
            explanation="Please try a different search query",
        )
        
    # Extract red flags and suggestions
    red_flags = []
    suggestions = []
    
    if final_response:
        rf_objs = final_response.get("red_flags", [])
        # Handle both list of strings and list of objects
        for rf in rf_objs:
            if isinstance(rf, str):
                red_flags.append(rf)
            elif isinstance(rf, dict):
                red_flags.append(rf.get("description", ""))
                
        suggestions_raw = final_response.get("follow_up_suggestions", [])
        if isinstance(suggestions_raw, list):
            # Handle list of strings or list of dicts
            for item in suggestions_raw:
                if isinstance(item, str):
                    suggestions.append(item)
                elif isinstance(item, dict):
                    # Try to find the suggestion text in common keys
                    sugg_text = item.get("suggestion") or item.get("text") or item.get("description") or str(item)
                    suggestions.append(sugg_text)
        elif isinstance(suggestions_raw, dict):
            # Handle case where LLM returns a dict wrapper like {'suggestions': [...]}
            inner_suggestions = suggestions_raw.get("suggestions", [])
            if isinstance(inner_suggestions, list):
                for item in inner_suggestions:
                    if isinstance(item, str):
                        suggestions.append(item)
                    elif isinstance(item, dict):
                        sugg_text = item.get("suggestion") or item.get("text") or item.get("description") or str(item)
                        suggestions.append(sugg_text)
        
    elif analysis_result:
        rf_objs = analysis_result.get("red_flags", [])
        for rf in rf_objs:
            if isinstance(rf, str):
                red_flags.append(rf)
            elif isinstance(rf, dict):
                red_flags.append(rf.get("description", ""))

    return ShoppingResponse(
        session_id=session_id,
        user_query=query,
        matched_products=products,
        recommendation=rec_info,
        alternatives=products[1:4] if len(products) > 1 else None,
        total_results=len(matched_products),
        search_metadata=result.get("metadata", {}),
        red_flags=red_flags,
        follow_up_suggestions=suggestions,
    )

@router.post("", response_model=ShoppingResponse)
async def search_products(
    request: ShoppingRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Synchronous search endpoint"""
    session = session_manager.get_or_create_session(
        session_id=request.session_id,
        user_id=request.user_preferences.get("user_id") if request.user_preferences else None
    )
    session_id = session.session_id
    
    # Use AsyncSqliteSaver for persistence
    async with aiosqlite.connect("data/checkpoints.db") as conn:
        checkpointer = AsyncSqliteSaver(conn)
        
        try:
            graph = build_graph(checkpointer=checkpointer)
            
            # Thread ID for persistence
            config = {"configurable": {"thread_id": session_id}}
            
            initial_state = {
                "user_query": request.query,
                "session_id": session_id,
                "user_preferences": session.user_preferences,
                "previous_queries": session.conversation_history.get_recent_queries(5),
            }
            
            # Use ainvoke for async execution
            result = await graph.ainvoke(initial_state, config)
            
            # Update memory
            matched_products = result.get("matched_products", [])
            rec = result.get("recommendation", {})
            top_rec = rec.get("product", {}).get("title") if rec else None
            
            ConversationMemory.add_turn_to_session(
                session,
                user_query=request.query,
                search_plan=result.get("search_plan"),
                products_found=len(matched_products),
                top_recommendation=top_rec,
            )
            session_manager.update_session(session)
            
            return format_shopping_response(session_id, request.query, result)
            
        except Exception as e:
            log_error(error_logger, e, f"Search failed for {session_id}")
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def search_products_stream(
    request: ShoppingRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Streaming search endpoint with HITL support"""
    session_id = request.session_id or str(uuid.uuid4())
    
    async def event_generator():
        logger.info(f"Starting event generator for session {session_id}")
        async with aiosqlite.connect("data/checkpoints.db") as conn:
            checkpointer = AsyncSqliteSaver(conn)
            
            try:
                yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
                logger.info("Yielded start event")
                
                graph = build_graph(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": session_id}}
                
                # Fetch session history for context-aware routing
                session = session_manager.get_or_create_session(
                    session_id=session_id,
                    user_id=request.user_preferences.get("user_id") if request.user_preferences else None
                )
                
                # Extract previous queries from session turns
                previous_queries = []
                for turn in session.conversation_history.turns[-5:]:  # Last 5 turns for context
                    if turn.user_query:
                        previous_queries.append(turn.user_query)
                
                initial_state = {
                    "user_query": request.query,
                    "session_id": session_id,
                    "previous_queries": previous_queries,
                }
                
                step_count = 0
                async for event in graph.astream_events(initial_state, config, version="v2"):
                    step_count += 1
                    # logger.info(f"Event received: {event.get('event')} - {event.get('name')}")
                    
                    # Progress events (Start of node)
                    if event.get("event") == "on_chain_start":
                        # Try to get graph node name from metadata first
                        metadata = event.get("metadata", {})
                        node_name = metadata.get("langgraph_node") or event.get("name", "")
                        
                        # Filter out internal LangGraph nodes
                        if node_name and node_name not in ["LangGraph", "RunnableSequence", "start", "__start__", "RunnableLambda"]:
                             logger.info(f"Yielding progress for node: {node_name}")
                             yield f"data: {json.dumps({'type': 'progress', 'step': step_count, 'node': node_name, 'message': f'Executing {node_name}'})}\n\n"
                    
                    # Output events (End of node)
                    if event.get("event") == "on_chain_end":
                        metadata = event.get("metadata", {})
                        node_name = metadata.get("langgraph_node") or event.get("name", "")
                        
                        if node_name and node_name not in ["LangGraph", "RunnableSequence", "start", "__start__", "RunnableLambda"]:
                            output_data = event.get("data", {}).get("output")
                            # Sanitize output for frontend (avoid huge objects)
                            # Send full output as requested by user
                            # For large objects like collection/analysis, we send the structured data
                            # Frontend will handle the display (scrollable)
                            if isinstance(output_data, dict):
                                safe_output = output_data
                            else:
                                safe_output = str(output_data)
                            
                            yield f"data: {json.dumps({'type': 'node_output', 'node': node_name, 'output': safe_output})}\n\n"

                    # Chunk events
                    if event.get("event") == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk", {})
                        if chunk:
                            yield f"data: {json.dumps({'type': 'chunk', 'content': str(chunk.content)})}\n\n"
                
                # Check if interrupted (HITL)
                snapshot = await graph.aget_state(config)
                if snapshot.next:
                    logger.info("Yielding interrupt event")
                    # Extract actual interrupt message if available
                    interrupt_msg = "Clarification needed"
                    if snapshot.tasks and snapshot.tasks[0].interrupts:
                        interrupt_value = snapshot.tasks[0].interrupts[0].value
                        if isinstance(interrupt_value, str):
                            interrupt_msg = interrupt_value
                    
                    yield f"data: {json.dumps({'type': 'interrupt', 'node': 'clarification', 'message': interrupt_msg, 'thread_id': session_id})}\n\n"
                else:
                    logger.info("Yielding complete event")
                    result = snapshot.values
                    
                    # CRITICAL: Save session turn for memory persistence
                    try:
                        products = result.get("products", [])
                        analysis_result = result.get("analysis_result", {})
                        top_rec_data = analysis_result.get("top_recommendation", {}) if analysis_result else {}
                        top_rec = top_rec_data.get("product_name") if isinstance(top_rec_data, dict) else None
                        
                        ConversationMemory.add_turn_to_session(
                            session,
                            user_query=request.query,
                            search_plan=result.get("search_plan"),
                            products_found=len(products),
                            top_recommendation=top_rec,
                        )
                        session_manager.update_session(session)
                        logger.info(f"Session updated with turn: {request.query}")
                    except Exception as save_error:
                        logger.error(f"Failed to save session turn: {save_error}")
                    
                    formatted_response = format_shopping_response(session_id, request.query, result)
                    response_dict = json.loads(formatted_response.json())
                    yield f"data: {json.dumps({'type': 'complete', 'result': response_dict})}\n\n"
                    yield "data: {\"type\": \"end\"}\n\n"
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/resume")
async def resume_search(
    request: ResumeRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Resume execution after interrupt"""
    async with aiosqlite.connect("data/checkpoints.db") as conn:
        checkpointer = AsyncSqliteSaver(conn)
        
        try:
            graph = build_graph(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": request.thread_id}}
            
            # Resume with user input
            # We use Command(resume=...) to provide the value expected by the interrupt
            result = await graph.ainvoke(
                Command(resume=request.user_input),
                config
            )
            
            return format_shopping_response(request.session_id, "Resumed", result)
            
        except Exception as e:
            log_error(error_logger, e, f"Resume failed for {request.thread_id}")
            raise HTTPException(status_code=500, detail=str(e))
