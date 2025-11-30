from typing import Dict, Any, List
from langgraph.types import interrupt
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot

def refine_search_criteria(state: AgentState) -> AgentState:
    """HITL Node: Ask user to refine search criteria."""
    query = state.get("user_query", "")
    
    msg = (
        f"I need a bit more detail to find the best results for '{query}'.\n"
        f"Could you specify:\n"
        f"- Budget range?\n"
        f"- Preferred brands?\n"
        f"- Key features you need?"
    )
    
    # Interrupt and wait for user input
    user_input = interrupt(msg)
    
    if user_input:
        # Update query with refinement
        state["user_query"] = f"{query} (Refinement: {user_input})"
        debug_notes = state.get("debug_notes", [])
        debug_notes.append(f"HITL: Search criteria refined: {user_input}")
        state["debug_notes"] = debug_notes
        
    return state

def adjust_strategy_handler(state: AgentState) -> AgentState:
    """HITL Node: Ask user to adjust strategy after poor results."""
    retry_count = state.get("retry_count", 0)
    
    msg = (
        f"I'm having trouble finding good matches (Attempt {retry_count}).\n"
        f"Should I:\n"
        f"1. Broaden the search?\n"
        f"2. Try a different keyword?\n"
        f"3. Or do you want to provide a specific product link?"
    )
    
    user_input = interrupt(msg)
    
    if user_input:
        # Update plan or query based on input
        # For simplicity, we append it to the query as a directive
        current_query = state.get("user_query", "")
        state["user_query"] = f"{current_query} (Strategy Adjustment: {user_input})"
        
        # Reset retry count to give it a fresh start
        state["retry_count"] = 0
        
        debug_notes = state.get("debug_notes", [])
        debug_notes.append(f"HITL: Strategy adjusted: {user_input}")
        state["debug_notes"] = debug_notes
        
    return state

def verify_analysis_handler(state: AgentState) -> AgentState:
    """HITL Node: Ask user to verify analysis if uncertain."""
    analysis = state.get("analysis_result", {})
    top_rec = analysis.get("top_recommendation", {}).get("product_name", "Unknown")
    
    msg = (
        f"Based on my analysis, I recommend **{top_rec}**.\n"
        f"Does this look right to you, or should I analyze the alternatives more deeply?"
    )
    
    user_input = interrupt(msg)
    
    if user_input and "analyze" in user_input.lower():
        # Flag to trigger deeper analysis or re-ranking
        state["analysis_error"] = "User requested deeper analysis"
        # Logic to handle this would go here, potentially looping back
    
    return state

def manual_search_handler(state: AgentState) -> AgentState:
    """HITL Node: Allow human to provide manual search data."""
    msg = "I'm stuck. Please provide a product link or search term manually."
    user_input = interrupt(msg)
    
    if user_input:
        # Treat input as a direct link or specific term
        state["user_query"] = user_input
        # Force a direct search route potentially
        state["route"] = "direct_search"
        
    return state
