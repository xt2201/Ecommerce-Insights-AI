"""Router Agent - Classifies queries and routes to appropriate workflow."""

from __future__ import annotations

from typing import Literal

from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.planning_models import QueryClassification
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot
from ai_server.memory.conversation_memory import ConversationMemory
from ai_server.utils.prompt_loader import load_prompt
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.utils.token_counter import extract_token_usage
from langgraph.types import interrupt


# Load prompts
_PROMPTS = load_prompt("router_agent_prompts")


def _get_prompt_section(prompt_name: str) -> str:
    """Extract specific prompt section from loaded prompts."""
    import re
    
    pattern = rf"## {prompt_name}.*?```template\n(.*?)```"
    match = re.search(pattern, _PROMPTS, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # Fallback
    lines = _PROMPTS.split('\n')
    in_section = False
    prompt_lines = []
    
    for line in lines:
        if f"## {prompt_name}" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith('##'):
                break
            if line.startswith('```') or line.endswith('```'):
                continue
            prompt_lines.append(line)
    
    return '\n'.join(prompt_lines).strip()


def classify_query(query: str, chat_history: list[str] = None) -> tuple[QueryClassification, dict]:
    """Classify query to determine routing.
    
    Args:
        query: User's search query
        chat_history: List of previous user queries
        
    Returns:
        Tuple of (QueryClassification, usage_dict) with route, confidence, reasoning and actual token usage
    """
    try:
        llm = get_llm(agent_name="router")
        # Dùng include_raw=True để lấy cả parsed result và raw AIMessage (có token usage)
        structured_llm = llm.with_structured_output(QueryClassification, include_raw=True)
        
        prompt_template = _get_prompt_section("Classify Query Type Prompt")
        
        # Format chat history
        history_str = "No previous history."
        if chat_history:
            history_str = "\n".join([f"- {q}" for q in chat_history[-5:]]) # Last 5 queries
            
        prompt = prompt_template.replace("{query}", query).replace("{chat_history}", history_str)
        
        # Invoke và nhận cả parsed + raw
        out = structured_llm.invoke(prompt)
        parsed = out["parsed"]  # QueryClassification object
        raw = out["raw"]        # AIMessage với response_metadata
        
        # Extract actual token usage từ raw AIMessage
        usage = extract_token_usage(raw)
        
        return parsed, usage
        
    except Exception as e:
        # Fallback: default to standard
        return QueryClassification(
            route="standard",
            confidence=0.5,
            reasoning=f"Classification failed ({e}), using standard route",
            is_followup=False,
            followup_reasoning="Fallback due to error"
        ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def router_node(state: AgentState) -> AgentState:
    """Router Node - Classifies query and updates state.
    
    This node performs the actual classification and stores the result in the state.
    The conditional edge will then read this state to determine the next step.
    """
    query = state.get("user_query", "")
    debug_notes = state.get("debug_notes", [])
    trace_manager = get_trace_manager()
    
    # Create trace if not exists
    trace_id = state.get("trace_id")
    if not trace_id:
        trace = trace_manager.create_trace(
            user_query=query,
            session_id=state.get("session_id")
        )
        state["trace_id"] = trace.trace_id
        trace_id = trace.trace_id
    
    # Create router step
    step = trace_manager.create_step(
        trace_id=trace_id,
        step_type=StepType.ROUTER,
        agent_name="router_agent"
    )
    
    route_decision = "planning" # Default
    
    try:
        # Get previous queries for context
        previous_queries = state.get("previous_queries", [])
        
        # DEBUG: Log what we're passing to the LLM
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Router: previous_queries = {previous_queries}")
        
        # Classify with history context
        classification, usage = classify_query(query, previous_queries)
        
        # Use LLM-detected follow-up status
        is_followup = classification.is_followup
        state["is_followup"] = is_followup
        
        if is_followup:
            debug_notes.append(f"Router: Detected follow-up query (Reason: {classification.followup_reasoning})")
            # For follow-ups, extract reference context if available
            if previous_queries:
                last_query = previous_queries[-1]
                state["reference_context"] = {
                    "last_query": last_query,
                    "is_followup": True,
                    "context_reasoning": classification.followup_reasoning
                }
                # Rewrite query to include context for the planner
                # This ensures the planner understands "cheaper" means "cheaper than [last_query]"
                new_query = f"{query} (Context: Previous query was '{last_query}')"
                state["user_query"] = new_query
                debug_notes.append(f"Router: Rewrote query with context: {new_query}")
        
        debug_notes.append(
            f"Router: {classification.route} "
            f"(confidence={classification.confidence:.2f}) - {classification.reasoning}"
        )
        
        # Log classification for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Router Classification: Route={classification.route}, "
            f"Confidence={classification.confidence}, "
            f"IsFollowup={is_followup}, "
            f"Reason={classification.reasoning}"
        )
        
        # PHASE 2 HITL: Low Confidence Check
        # If confidence is low (< 0.7) and not already asking for clarification,
        # interrupt to confirm intent.
        if classification.confidence < 0.7 and classification.route != "clarification":
            debug_notes.append(f"Router: Low confidence ({classification.confidence:.2f}). Triggering HITL.")
            
            clarification_msg = (
                f"I'm not entirely sure I understood that. "
                f"I think you want to '{classification.route}' regarding '{query}'. "
                f"Is that correct? Or could you clarify?"
            )
            
            # Interrupt
            user_feedback = interrupt(clarification_msg)
            
            if user_feedback:
                debug_notes.append(f"Router: Resumed with feedback: {user_feedback}")
                # Append feedback to query and re-classify
                # (Or we could trust the user's explicit direction if we parsed it, 
                # but re-classifying with more context is safer)
                query = f"{query} (Context: {user_feedback})"
                state["user_query"] = query
                
                # Re-classify with updated query
                classification, usage = classify_query(query, previous_queries)
                debug_notes.append(f"Router: Re-classified as {classification.route} ({classification.confidence:.2f})")

        # Map routes
        # CRITICAL: If this is a follow-up, override clarification route
        # Follow-ups like "cheaper" rely on context, not standalone clarity
        if is_followup and classification.route == "clarification":
            debug_notes.append(
                f"Router: Overriding 'clarification' to 'planning' for follow-up query. "
                f"Context will resolve ambiguity."
            )
            route_decision = "planning"
        elif classification.route == "direct_search":
            route_decision = "direct_search"
        elif classification.route == "clarification":
            route_decision = "clarification"
        elif classification.route in ["chitchat", "faq", "advisory", "feedback"]:
            route_decision = classification.route
        else:  # planning
            route_decision = "planning"
            
        # Update state
        state["route"] = classification.route
        state["route_decision"] = route_decision
        state["confidence"] = classification.confidence
        state["reasoning"] = classification.reasoning
        
        # Complete step with success
        if step:
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={
                    "route": route_decision,
                    "classification": classification.route,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                    "is_followup": is_followup
                },
                token_usage=TokenUsage(
                    prompt_tokens=usage.get("input_tokens", 0),
                    completion_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
            )
            
    except Exception as e:
        # Fail step on error
        if step:
            trace_manager.fail_step(
                trace_id=trace_id,
                step_id=step.step_id,
                error=str(e)
            )
        
        # Default to planning on error
        debug_notes.append(f"Router error: {e}, defaulting to planning")
        state["route_decision"] = "planning"
        
    state["debug_notes"] = debug_notes
    return state


def route_query(state: AgentState) -> Literal["planning", "direct_search", "clarification", "chitchat", "faq", "advisory"]:
    """Conditional edge function to select the next node based on state."""
    return state.get("route_decision", "planning")


def quick_search_handler(state: AgentState) -> AgentState:
    """Quick search for simple queries.
    
    Skips planning and uses query directly as keyword.
    """
    query = state.get("user_query", "")
    
    state["search_plan"] = {
        "keywords": [query],
        "amazon_domain": "amazon.com",
        "max_price": None,
        "engines": ["amazon"],
        "asin_focus_list": [],
        "notes": "Quick search (specific product name, no planning needed)"
    }
    
    debug_notes = state.get("debug_notes", [])
    debug_notes.append("Using quick search path (simple query)")
    state["debug_notes"] = debug_notes
    
    return state


def request_clarification_handler(state: AgentState) -> AgentState:
    """Request clarification for vague queries.
    
    Returns a response asking user for more details.
    """
    query = state.get("user_query", "")
    
    clarification_message = (
        f"Tôi cần thêm thông tin để giúp bạn tìm kiếm tốt hơn.\n\n"
        f"Bạn đã nói: '{query}'\n\n"
        f"Vui lòng cung cấp:\n"
        f"• Loại sản phẩm cụ thể bạn đang tìm?\n"
        f"• Ngân sách của bạn là bao nhiêu?\n"
        f"• Có tính năng nào bạn cần không?\n"
        f"• Có thương hiệu ưa thích không?\n\n"
        f"Ví dụ: 'tai nghe bluetooth dưới $100 với chống ồn'"
    )
    
    state["response"] = ResponsePayload(
        summary=clarification_message,
        recommendations=[],
        analysis=AnalysisSnapshot(
            cheapest=None,
            highest_rated=None,
            best_value=None,
            noteworthy_insights=["Query requires clarification"]
        ),
        raw_products=[]
    )
    
    debug_notes = state.get("debug_notes", [])
    debug_notes.append("Requesting clarification (vague query)")
    state["debug_notes"] = debug_notes
    
    # PHASE 3 HITL: Interrupt execution to wait for user input
    # The value returned by interrupt() will be the user's input when resumed
    user_answer = interrupt(clarification_message)
    
    # Update query with clarification
    if user_answer:
        original_query = state.get("user_query", "")
        new_query = f"{original_query} (User Clarification: {user_answer})"
        state["user_query"] = new_query
        debug_notes.append(f"Resumed with clarification: {user_answer}")
        state["debug_notes"] = debug_notes
    
    return state
