"""Context-aware planning agent - Phase 3.2 enhancement."""

from typing import Dict, List, Optional

from ai_server.tools.planning_tools import (
    analyze_query_intent,
    expand_keywords,
    extract_requirements,
)
from ai_server.memory.conversation_memory import ConversationMemory
from ai_server.memory.preference_extractor import PreferenceExtractor
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.memory_models import ConversationTurn
from ai_server.utils.logger import get_agent_logger

logger = get_agent_logger()


class ContextAwarePlanner:
    """Enhanced planning that uses conversation history and user preferences."""
    
    def __init__(self):
        """Initialize context-aware planner."""
        self.preference_extractor = PreferenceExtractor()
        logger.debug("ContextAwarePlanner initialized")
    
    def plan_with_context(self, state: AgentState) -> Dict:
        """Create search plan using conversation context and preferences.
        
        Args:
            state: Agent state with conversation history and preferences
            
        Returns:
            Enhanced search plan
        """
        query = state["user_query"]
        conversation_history = state.get("conversation_history", [])
        user_preferences = state.get("user_preferences", {})
        is_followup = state.get("is_followup", False)
        session_id = state.get("session_id", "unknown")
        
        logger.info(
            f"Planning with context",
            extra={
                "session_id": session_id,
                "query": query,
                "is_followup": is_followup,
                "has_history": bool(conversation_history),
                "has_preferences": bool(user_preferences)
            }
        )
        
        # Convert conversation history to ConversationTurn objects
        previous_turns = [
            ConversationTurn.from_dict(turn) 
            for turn in conversation_history
        ] if conversation_history else []
        
        # Check if this is a follow-up query
        if is_followup and previous_turns:
            return self._plan_followup_query(
                query, 
                previous_turns,
                user_preferences,
                session_id
            )
        
        # Regular query planning with preference awareness
        return self._plan_regular_query(query, user_preferences)
    
    def _plan_followup_query(
        self,
        query: str,
        previous_turns: List[ConversationTurn],
        user_preferences: Dict,
        session_id: str = "unknown"
    ) -> Dict:
        """Plan a follow-up query using context from previous turns.
        
        Args:
            query: Current query (e.g., "cheaper version")
            previous_turns: Previous conversation turns
            user_preferences: User preferences dictionary
            session_id: Session ID for logging
            
        Returns:
            Context-aware search plan
        """
        logger.info(
            f"Planning follow-up query",
            extra={
                "session_id": session_id,
                "query": query,
                "previous_turns_count": len(previous_turns)
            }
        )
        
        # Get reference context
        reference_context = ConversationMemory.extract_reference_context(
            query,
            previous_turns
        )
        
        last_turn = previous_turns[-1]
        base_query = last_turn.user_query
        modification = reference_context.get("modification", "unknown")
        
        logger.debug(
            f"Follow-up context",
            extra={
                "session_id": session_id,
                "base_query": base_query,
                "modification": modification
            }
        )
        
        # Modify query based on context
        if modification == "reduce_price":
            # Extract price from previous query or use preference
            reference_price = reference_context.get("reference_price")
            if not reference_price and last_turn.search_plan:
                reference_price = last_turn.search_plan.get("max_price")
            
            if reference_price:
                # Reduce price by 20-30%
                new_max_price = reference_price * 0.7
                enhanced_query = f"{base_query} under ${new_max_price:.0f}"
            else:
                enhanced_query = f"budget {base_query}"
            
            logger.debug(
                f"Enhanced query for price reduction",
                extra={
                    "session_id": session_id,
                    "enhanced_query": enhanced_query,
                    "reference_price": reference_price
                }
            )
            
        elif modification == "increase_price":
            enhanced_query = f"premium {base_query}"
            
        elif modification == "add_wireless":
            enhanced_query = f"wireless {base_query}"
            
        elif modification == "add_feature":
            # Extract feature from current query
            enhanced_query = f"{base_query} {query}"
            
        elif modification == "remove_feature":
            enhanced_query = base_query
            
        elif modification == "similar_products":
            enhanced_query = base_query
            
        else:
            # Default: append modification to base query
            enhanced_query = f"{base_query} {query}"
        
        # Now plan using the enhanced query
        return self._plan_regular_query(enhanced_query, user_preferences)
    
    def _plan_regular_query(
        self,
        query: str,
        user_preferences: Dict
    ) -> Dict:
        """Plan a regular (non-follow-up) query with preference awareness.
        
        Args:
            query: User query
            user_preferences: User preferences dictionary
            
        Returns:
            Search plan with applied preferences
        """
        # Extract preferences from current query
        extracted_prefs = self.preference_extractor._rule_based_extraction(query)
        
        # Step 1: Analyze intent
        intent_analysis = analyze_query_intent(query)
        logger.info(
            f"Query intent analysis",
            extra={
                "query": query,
                "intent": str(intent_analysis),
                "specificity": str(getattr(intent_analysis, 'specificity', 'N/A'))
            }
        )
        
        # Step 2: Expand keywords if needed
        keywords_result = None
        specificity = getattr(intent_analysis, 'specificity', 1.0)
        if isinstance(specificity, (int, float)) and specificity < 0.7:
            keywords_result = expand_keywords(query)
            logger.debug(f"Expanded keywords: {keywords_result}", extra={"query": query})
        
        # Step 3: Extract requirements
        requirements = extract_requirements(query)
        logger.info(
            f"Requirements extracted",
            extra={
                "query": query,
                "requirements": str(requirements)
            }
        )
        
        # Step 4: Apply user preferences
        enhanced_requirements = self._apply_preferences(
            requirements if isinstance(requirements, dict) else {},
            extracted_prefs,
            user_preferences
        )
        
        # Build search plan
        if keywords_result and isinstance(keywords_result, dict):
            search_keywords = keywords_result.get("keywords", [query])
        else:
            search_keywords = [query]
        
        search_plan = {
            "keywords": search_keywords,
            "max_price": enhanced_requirements.get("max_price"),
            "min_rating": enhanced_requirements.get("min_rating"),
            "preferred_brands": enhanced_requirements.get("preferred_brands", []),
            "required_features": enhanced_requirements.get("required_features", []),
            "nice_to_have_features": enhanced_requirements.get("nice_to_have_features", []),
            "amazon_domain": "amazon.com",
            "engines": ["amazon"],
        }
        
        return {
            "search_plan": search_plan,
            "intent_analysis": intent_analysis,
            "extracted_preferences": extracted_prefs.model_dump(),
            "applied_user_preferences": len(user_preferences.get("liked_brands", {})) > 0,
        }
    
    def _apply_preferences(
        self,
        requirements: Dict,
        extracted_prefs,
        user_preferences: Dict
    ) -> Dict:
        """Apply user preferences to requirements.
        
        Args:
            requirements: Extracted requirements from query
            extracted_prefs: Preferences extracted from current query
            user_preferences: Historical user preferences
            
        Returns:
            Enhanced requirements with preferences applied
        """
        enhanced = requirements.copy()
        
        # Apply price preferences
        if not enhanced.get("max_price") and user_preferences.get("max_budget"):
            enhanced["max_price"] = user_preferences["max_budget"]
            logger.debug(f"Applied user max budget: ${user_preferences['max_budget']}")
        
        # Apply brand preferences (top 3 liked brands)
        liked_brands = user_preferences.get("liked_brands", {})
        if liked_brands and not extracted_prefs.brands:
            top_brands = sorted(liked_brands.items(), key=lambda x: x[1], reverse=True)[:3]
            enhanced["preferred_brands"] = [brand for brand, _ in top_brands]
            logger.debug(f"Applied preferred brands: {enhanced['preferred_brands']}")
        elif extracted_prefs.brands:
            enhanced["preferred_brands"] = extracted_prefs.brands
        
        # Apply feature preferences
        must_have_features = user_preferences.get("must_have_features", {})
        if must_have_features:
            top_features = sorted(must_have_features.items(), key=lambda x: x[1], reverse=True)[:5]
            user_must_have = [feat for feat, conf in top_features if conf > 0.5]
            
            # Merge with query features
            current_features = enhanced.get("required_features", [])
            enhanced["required_features"] = list(set(current_features + user_must_have))
            
            if user_must_have:
                logger.debug(f"Applied user must-have features: {user_must_have}")
        
        # Apply rating preferences
        if not enhanced.get("min_rating") and user_preferences.get("min_rating"):
            enhanced["min_rating"] = user_preferences["min_rating"]
            logger.debug(f"Applied user min rating: {user_preferences['min_rating']}")
        
        return enhanced
