"""Planning Agent - Autonomous agent with tools and structured outputs."""

from __future__ import annotations

import json
from typing import Dict

from ai_server.core.config import load_config
from ai_server.llm import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.memory.preference_extractor import PreferenceExtractor
from ai_server.tools.planning_tools import (
    analyze_query_intent,
    expand_keywords,
    extract_requirements,
    generate_comprehensive_plan_with_tokens,
)
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage

# Initialize preference extractor (reused across calls)
_preference_extractor = None


def _get_preference_extractor() -> PreferenceExtractor:
    """Get or create preference extractor instance."""
    global _preference_extractor
    if _preference_extractor is None:
        _preference_extractor = PreferenceExtractor()
    return _preference_extractor


def plan_search(state: AgentState) -> AgentState:
    """Enhanced planning with autonomous tool usage.
    
    Uses ReAct-style reasoning with tools to create comprehensive search plans.
    """
    query = state.get("user_query", "").strip()
    if not query:
        raise ValueError("user_query required")
    
    debug_notes = state.get("debug_notes", [])
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create planning step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.PLANNING,
            agent_name="planning_agent"
        )
    
    try:
        # Single comprehensive analysis step
        debug_notes.append("Planning: Generating comprehensive plan...")
        
        # Use the version that returns tokens for tracking
        plan_result, total_tokens = generate_comprehensive_plan_with_tokens(query)
        
        # Extract components
        intent_analysis = plan_result.get("intent_analysis", {})
        keywords = plan_result.get("keywords", [query])
        requirements = plan_result.get("requirements", {})
        reasoning = plan_result.get("reasoning", "")
        
        # Log reasoning
        if reasoning:
            debug_notes.append(f"Planning Logic: {reasoning}")
        
        # Step 4: Extract preferences using PreferenceExtractor (still useful for long-term memory)
        # We can optimize this later or use the extracted requirements to populate it
        debug_notes.append("Planning: Updating user preferences...")
        preference_extractor = _get_preference_extractor()
        
        # Use extracted requirements to update preferences directly without another LLM call
        # This is a further optimization to avoid the preference_extractor LLM call
        user_preferences = state.get("user_preferences")
        if user_preferences:
            # Update brand preferences
            for brand in requirements.get("brand_preferences", []):
                user_preferences.update_brand_preference(brand, liked=True, confidence=0.8)
            
            # Update feature preferences
            for feature in requirements.get("required_features", []):
                user_preferences.update_feature_preference(feature, must_have=True, confidence=0.8)
            
            # Update price preferences
            if requirements.get("max_price"):
                user_preferences.update_price_preference(requirements.get("max_price"))
            
            # Update overall confidence
            user_preferences.confidence = min(1.0, user_preferences.confidence + 0.1)
            
            debug_notes.append(
                f"Planning: Updated preferences from plan (confidence: {user_preferences.confidence:.2f})"
            )
        
        # Step 5: Build search plan
        # Safe format with None handling
        specificity = intent_analysis.get('specificity', 0.5)
        confidence = intent_analysis.get('confidence', 0.5)
        
        # Determine engines based on intent
        engines = ["amazon"]
        intent_lower = str(intent_analysis.get('intent', '')).lower()
        query_lower = query.lower()
        
        # Note: Specialized engines like amazon_product_reviews are not supported by all plans
        # We rely on the main 'amazon' engine which provides basic review data
        debug_notes.append("Planning: Using standard amazon engine")

        search_plan = {
            "keywords": keywords[:5],  # Max 5 keywords
            "amazon_domain": "amazon.com",
            "max_price": requirements.get("max_price"),
            "engines": engines,
            "asin_focus_list": [],
            "notes": (
                f"Intent: {intent_analysis.get('intent')} "
                f"| Specificity: {specificity:.2f} "
                f"| Confidence: {confidence:.2f}"
            ),
            # Store requirements for analysis agent
            "requirements": requirements,
            "intent": intent_analysis
        }
        
        # Add features to notes if present
        features = requirements.get("required_features", [])
        if features:
            search_plan["notes"] += f" | Features: {', '.join(features)}"
        
        # Add brand preferences to notes if present
        brands = requirements.get("brand_preferences", [])
        if brands:
            search_plan["notes"] += f" | Brands: {', '.join(brands)}"
        
        state["search_plan"] = search_plan
        state["debug_notes"] = debug_notes
        
        debug_notes.append(
            f"Planning: Created plan with {len(keywords)} keywords "
            f"(confidence={confidence:.2f})"
        )
        debug_notes.append(f"Planning: Token usage: {total_tokens}")
        
        # Complete step with success and actual token usage
        if trace_id and step:
            total = total_tokens.get("total_tokens", 0)
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={
                    "search_plan": search_plan,
                    "intent_analysis": intent_analysis,
                    "requirements": requirements,
                    "keywords_count": len(keywords)
                },
                token_usage=TokenUsage(
                    prompt_tokens=total_tokens.get("input_tokens", 0),
                    completion_tokens=total_tokens.get("output_tokens", 0),
                    total_tokens=total
                )
            )
        
    except Exception as e:
        # Fail step on error
        if trace_id and step:
            trace_manager.fail_step(
                trace_id=trace_id,
                step_id=step.step_id,
                error=str(e)
            )
        
        # Fallback to simple plan
        debug_notes.append(f"Planning failed: {e}, using fallback")
        
        from ai_server.agents.planning_agent import _fallback_plan
        plan = _fallback_plan(query)
        state["search_plan"] = plan
        state["debug_notes"] = debug_notes
    
    return state
