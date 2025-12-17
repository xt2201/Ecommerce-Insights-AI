
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
    # Extract products from SharedWorkspace
    candidates = result.get("candidates", [])
    
    # Extract final report
    final_report = result.get("artifacts", {}).get("final_report", {})
    
    products = []
    for c in candidates[:10]:
        # Map ProductCandidate to ProductInfo
        p_data = c.source_data
        products.append(ProductInfo(
            title=c.title,
            link=p_data.get("link", ""),
            price=f"${c.price:.2f}" if c.price is not None else "N/A",
            rating=p_data.get("rating"),
            reviews=p_data.get("reviews_count"),
            image=p_data.get("thumbnail"),
            thumbnail=p_data.get("thumbnail"),
        ))
    
    # Construct recommendation info
    rec_info = None
    
    if final_report:
        top_picks = final_report.get("top_picks", [])
        if top_picks:
            top_pick = top_picks[0]
            # We need to find the full product info for the top pick
            # top_pick is a dict from ProductCandidate.dict()
            
            rec_info = RecommendationInfo(
                recommended_product=ProductInfo(
                    title=top_pick.get("title", ""),
                    link=top_pick.get("source_data", {}).get("link", ""),
                    price=f"${top_pick.get('price', 0):.2f}" if top_pick.get("price") is not None else "N/A",
                ),
                value_score=top_pick.get("domain_score", 0.0),
                reasoning=f"Selected as the best match for '{query}'",
                explanation=final_report.get("summary", ""),
                tradeoff_analysis="Trade-off analysis not available in this version."
            )
            
    if not rec_info:
        rec_info = RecommendationInfo(
            recommended_product=products[0] if products else ProductInfo(title="No products found", link="", price="$0.00"),
            value_score=0.0,
            reasoning="No recommendation generated.",
            explanation="No suitable products found.",
        )
        
    return ShoppingResponse(
        session_id=session_id,
        user_query=query,
        matched_products=products,
        recommendation=rec_info,
        alternatives=products[1:4] if len(products) > 1 else None,
        total_results=len(products),
        search_metadata={},
        red_flags=[],
        follow_up_suggestions=final_report.get("follow_up_suggestions", ["Try refining your search query."]) if final_report else ["Try refining your search query."],
    )

def to_serializable(obj):
    """Recursively convert Pydantic models to dicts"""
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return obj

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
            
            # Initialize SharedWorkspace
            from ai_server.schemas.shared_workspace import SharedWorkspace, DevelopmentPlan
            # Create initial state with session context
            initial_state = SharedWorkspace(
                goal=request.query,
                user_message=request.query,
                plan=DevelopmentPlan(goal=request.query, steps=[]),
                conversation=session.conversation_context  # Load persistent context
            )
            
            # Use ainvoke for async execution
            # Note: LangGraph invoke accepts dict or object. SharedWorkspace is Pydantic.
            # We pass the object directly.
            # Execute graph
            final_state = await graph.ainvoke(initial_state, config)
            
            # Persist updated conversation context
            if "conversation" in final_state:
                session.conversation_context = final_state["conversation"]
                session_manager.update_session(session)
            
            # --- PHASE 2 MEMORY INTEGRATION ---
            # Update session history
            ConversationMemory.add_turn_to_session(
                session=session,
                user_query=request.query,
                products_found=len(final_state.get("candidates", [])),
                top_recommendation=final_state.get("artifacts", {}).get("final_report", {}).get("summary")
            )
            session_manager.update_session(session) # Update session again after adding turn
            
            return format_shopping_response(session_id, request.query, final_state)
            
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
                
                graph = build_graph(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": session_id}}
                
                session = session_manager.get_or_create_session(
                    session_id=session_id,
                    user_id=request.user_preferences.get("user_id") if request.user_preferences else None
                )
                
                # Initialize SharedWorkspace
                from ai_server.schemas.shared_workspace import SharedWorkspace, DevelopmentPlan
                initial_state = SharedWorkspace(
                    goal=request.query,
                    user_message=request.query,
                    plan=DevelopmentPlan(goal=request.query, steps=[]),
                    conversation=session.conversation_context  # Load persistent context
                )
                
                # Internal LangChain components to filter out
                INTERNAL_CHAIN_NAMES = [
                    "LangGraph", "RunnableSequence", "RunnableLambda", "RunnableBinding",
                    "RunnableParallel", "RunnablePassthrough", "PromptTemplate",
                    "ChatOpenAI", "ChatAnthropic", "ChatGroq", "ChatMistral", "ChatCohere",
                    "start", "__start__", "__end__", "StrOutputParser", "JsonOutputParser"
                ]
                
                # Node information with icons, labels, and colors
                NODE_INFO = {
                    'understand': {'icon': '🧠', 'label': 'Hiểu yêu cầu', 'color': 'from-violet-500 to-purple-500', 'message': 'Đang phân tích yêu cầu của bạn'},
                    'greeting': {'icon': '👋', 'label': 'Chào hỏi', 'color': 'from-pink-500 to-rose-500', 'message': 'Đang chào hỏi và chuẩn bị'},
                    'search': {'icon': '🔍', 'label': 'Tìm kiếm', 'color': 'from-blue-500 to-cyan-500', 'message': 'Đang tìm kiếm sản phẩm'},
                    'analyze': {'icon': '📊', 'label': 'Phân tích', 'color': 'from-indigo-500 to-blue-500', 'message': 'Đang phân tích dữ liệu sản phẩm'},
                    'analyze_and_report': {'icon': '📈', 'label': 'Phân tích & Báo cáo', 'color': 'from-purple-500 to-indigo-500', 'message': 'Đang phân tích và tạo báo cáo'},
                    'consultation': {'icon': '💬', 'label': 'Tư vấn', 'color': 'from-green-500 to-emerald-500', 'message': 'Đang tư vấn'},
                    'clarification': {'icon': '❓', 'label': 'Làm rõ', 'color': 'from-yellow-500 to-amber-500', 'message': 'Đang làm rõ thông tin'},
                    'synthesize': {'icon': '✨', 'label': 'Tổng hợp', 'color': 'from-purple-500 to-pink-500', 'message': 'Đang tổng hợp kết quả'},
                    'faq': {'icon': '📚', 'label': 'Câu hỏi thường gặp', 'color': 'from-teal-500 to-cyan-500', 'message': 'Đang tra cứu câu hỏi thường gặp'},
                    'pre_search': {'icon': '🎯', 'label': 'Chuẩn bị', 'color': 'from-sky-500 to-blue-500', 'message': 'Đang chuẩn bị tìm kiếm'},
                    'collection': {'icon': '📦', 'label': 'Thu thập', 'color': 'from-amber-500 to-orange-500', 'message': 'Đang thu thập dữ liệu'},
                    'advisor': {'icon': '💡', 'label': 'Cố vấn', 'color': 'from-emerald-500 to-green-500', 'message': 'Đang đưa ra tư vấn'},
                    'reviewer': {'icon': '✅', 'label': 'Xem xét', 'color': 'from-teal-500 to-green-500', 'message': 'Đang xem xét kết quả'},
                }
                
                step_count = 0
                async for event in graph.astream_events(initial_state, config, version="v2"):
                    try:
                        step_count += 1
                        
                        # Progress events (Start of node)
                        if event.get("event") == "on_chain_start":
                            metadata = event.get("metadata", {})
                            # Only emit events with langgraph_node metadata (actual graph nodes)
                            node_name = metadata.get("langgraph_node")
                            
                            if node_name and node_name not in INTERNAL_CHAIN_NAMES:
                                node_info = NODE_INFO.get(node_name, {
                                    'icon': '⚙️',
                                    'label': 'Hệ thống',
                                    'color': 'from-gray-400 to-gray-500',
                                    'message': f'Đang xử lý {node_name}'
                                })
                                yield f"data: {json.dumps({
                                    'type': 'progress',
                                    'step': step_count,
                                    'node': node_name,
                                    'icon': node_info['icon'],
                                    'label': node_info['label'],
                                    'color': node_info['color'],
                                    'message': node_info['message']
                                })}\n\n"
                        
                        # Output events (End of node)
                        if event.get("event") == "on_chain_end":
                            metadata = event.get("metadata", {})
                            # Only emit events with langgraph_node metadata (actual graph nodes)
                            node_name = metadata.get("langgraph_node")
                            
                            if node_name and node_name not in INTERNAL_CHAIN_NAMES:
                                output_data = event.get("data", {}).get("output")
                                safe_output = to_serializable(output_data)
                                
                                yield f"data: {json.dumps({'type': 'node_output', 'node': node_name, 'output': safe_output}, default=str)}\n\n"
                    except Exception as e:
                        logger.error(f"Error in stream event processing: {e}")

                # Check if interrupted (HITL) - Not implemented in Antigravity yet, but keeping structure
                snapshot = await graph.aget_state(config)
                if snapshot.next:
                    yield f"data: {json.dumps({'type': 'interrupt', 'node': 'clarification', 'message': 'Clarification needed', 'thread_id': session_id})}\n\n"
                else:
                    logger.info("Yielding complete event")
                    result = snapshot.values
                    
                    # Save session turn
                    try:
                        candidates = result.get("candidates", [])
                        final_report = result.get("artifacts", {}).get("final_report", {})
                        top_picks = final_report.get("top_picks", [])
                        top_rec = top_picks[0].get("title") if top_picks else None
                        
                        ConversationMemory.add_turn_to_session(
                            session,
                            user_query=request.query,
                            search_plan={"goal": request.query},
                            products_found=len(candidates),
                            top_recommendation=top_rec,
                        )
                        session_manager.update_session(session)
                    except Exception as save_error:
                        logger.error(f"Failed to save session turn: {save_error}")
                    
                    formatted_response = format_shopping_response(session_id, request.query, result)
                    response_dict = json.loads(formatted_response.json())
                    yield f"data: {json.dumps({'type': 'complete', 'result': response_dict})}\n\n"
                    yield "data: {\"type\": \"end\"}\n\n"
                                
                # Persist updated conversation context after stream ends
                try:
                    # Retrieve final state from checkpointer
                    final_state_snapshot = await graph.aget_state(config)
                    if final_state_snapshot and final_state_snapshot.values:
                        final_context = final_state_snapshot.values.get("conversation")
                        if final_context:
                            session.conversation_context = final_context
                            session_manager.update_session(session)
                            logger.info(f"Updated session {session.session_id} context")
                            
                            # Also update conversation history (Phase 2)
                            candidates = final_state_snapshot.values.get("candidates", [])
                            artifacts = final_state_snapshot.values.get("artifacts", {})
                            report = artifacts.get("final_report", {})
                            summary = report.get("summary") if isinstance(report, dict) else str(report)
                            
                            ConversationMemory.add_turn_to_session(
                                session=session,
                                user_query=request.query,
                                products_found=len(candidates),
                                top_recommendation=summary
                            )
                            session_manager.update_session(session) # Update session again after adding turn
                except Exception as e:
                    logger.error(f"Failed to persist session context: {e}")

                # Send completion event
                yield f"data: {json.dumps({'type': 'complete', 'result': {'status': 'completed'}})}\n\n"
            
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
