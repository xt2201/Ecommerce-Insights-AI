"""Conversation memory and context management."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_server.schemas.agent_state import AgentState, SearchPlan
from ai_server.schemas.memory_models import ConversationTurn, SessionState
from ai_server.memory.context_manager import get_context_manager


class ConversationMemory:
    """Manages conversation history and context extraction."""
    
    @staticmethod
    def add_turn_to_session(
        session: SessionState,
        user_query: str,
        search_plan: Optional[SearchPlan] = None,
        products_found: int = 0,
        top_recommendation: Optional[str] = None,
        matched_products: List[Dict[str, Any]] = None,
        user_feedback: Optional[str] = None,
    ) -> None:
        """Add a new conversation turn to the session.
        
        Args:
            session: Session to update
            user_query: User's query
            search_plan: Generated search plan
            products_found: Number of products found
            top_recommendation: Top recommended product
            matched_products: List of matched products (dicts)
            user_feedback: User feedback on the recommendation
        """
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_query=user_query,
            search_plan=search_plan,
            products_found=products_found,
            top_recommendation=top_recommendation,
            matched_products=matched_products or [],
            user_feedback=user_feedback,
        )
        
        session.add_turn(turn)
        
        # Update Context Manager (Vector DB + Summary)
        try:
            get_context_manager().add_turn(session, turn)
        except Exception as e:
            # Don't fail the request if memory update fails
            print(f"Failed to update context manager: {e}")
    
    @staticmethod
    def get_context_for_state(session: SessionState, max_turns: int = 5, current_query: Optional[str] = None) -> Dict[str, any]:
        """Extract context from session for agent state.
        
        Args:
            session: Session to extract context from
            max_turns: Maximum number of recent turns to include
            current_query: Current user query (for semantic retrieval)
            
        Returns:
            Dictionary with context information
        """
        recent_turns = session.conversation_history.get_recent_turns(max_turns)
        
        # Semantic Retrieval
        relevant_history = []
        if current_query:
            try:
                relevant_history = get_context_manager().get_semantic_context(session.session_id, current_query)
            except Exception as e:
                print(f"Failed to retrieve semantic context: {e}")
        
        return {
            "previous_queries": [turn.user_query for turn in recent_turns],
            "previous_recommendations": [
                turn.top_recommendation 
                for turn in recent_turns 
                if turn.top_recommendation
            ],
            "conversation_summary": session.context_summary or ConversationMemory._summarize_conversation(recent_turns),
            "relevant_history": relevant_history,
        }
    
    @staticmethod
    def _summarize_conversation(turns: List[ConversationTurn]) -> str:
        """Create a summary of recent conversation turns.
        
        Args:
            turns: List of conversation turns
            
        Returns:
            Summary string
        """
        if not turns:
            return "No previous conversation"
        
        summary_parts = []
        for i, turn in enumerate(turns[-3:], 1):  # Last 3 turns
            summary_parts.append(
                f"Turn {i}: User asked '{turn.user_query}'. "
                f"Found {turn.products_found} products."
            )
        
        return " ".join(summary_parts)
    
    @staticmethod
    def is_followup_query(current_query: str, previous_queries: List[str]) -> bool:
        """Detect if current query is a follow-up to previous queries.
        
        Args:
            current_query: Current user query
            previous_queries: List of previous queries
            
        Returns:
            True if query appears to be a follow-up
        """
        if not previous_queries:
            return False
        
        # Keywords that indicate follow-up
        followup_keywords = [
            "cheaper", "more expensive", "similar", "but", 
            "instead", "different", "another", "also",
            "what about", "how about", "compared to",
            "without", "with", "or", "versus", "vs"
        ]
        
        query_lower = current_query.lower()
        
        # Check for follow-up keywords
        has_followup_keyword = any(keyword in query_lower for keyword in followup_keywords)
        
        # Check for pronouns that reference previous context
        has_reference_pronoun = any(
            word in query_lower.split()
            for word in ["it", "them", "those", "these", "that", "this"]
        )
        
        # Very short queries are often follow-ups
        is_very_short = len(current_query.split()) <= 3
        
        return has_followup_keyword or has_reference_pronoun or (is_very_short and len(previous_queries) > 0)
    
    @staticmethod
    def extract_reference_context(
        current_query: str, 
        previous_turns: List[ConversationTurn]
    ) -> Dict[str, any]:
        """Extract context references from current query.
        
        Args:
            current_query: Current user query
            previous_turns: Previous conversation turns
            
        Returns:
            Dictionary with reference context
        """
        if not previous_turns:
            return {}
        
        last_turn = previous_turns[-1]
        query_lower = current_query.lower()
        
        context = {
            "referenced_query": last_turn.user_query,
            "referenced_plan": last_turn.search_plan,
        }
        
        # Detect specific reference types
        if "cheaper" in query_lower or "budget" in query_lower:
            context["modification"] = "reduce_price"
            if last_turn.search_plan and last_turn.search_plan.get("max_price"):
                context["reference_price"] = last_turn.search_plan["max_price"]
        
        elif "more expensive" in query_lower or "premium" in query_lower:
            context["modification"] = "increase_price"
        
        elif "wireless" in query_lower and "wired" not in last_turn.user_query.lower():
            context["modification"] = "add_wireless"
        
        elif "similar" in query_lower:
            context["modification"] = "similar_products"
        
        elif any(word in query_lower for word in ["without", "no", "don't need"]):
            context["modification"] = "remove_feature"
        
        elif any(word in query_lower for word in ["with", "add", "also"]):
            context["modification"] = "add_feature"
        
        return context
