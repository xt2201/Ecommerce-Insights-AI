"""
LLM Router

Routes requests to appropriate agents based on QueryUnderstanding.
Includes information completeness check for consultative shopping flow.
"""
from __future__ import annotations

import logging
from typing import Literal

from ai_server.agents.query_understanding_agent import QueryUnderstanding
from ai_server.schemas.session_memory import SessionMemory
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


# Available routes - added pre_search_consultation for consultative flow
RouteType = Literal[
    "greeting",                 # Handle greeting
    "search",                   # Execute product search
    "consultation",             # Discuss shown products
    "clarification",            # Ask for more info
    "pre_search_consultation",  # Advise before searching
    "faq",                      # FAQ tool call
    "order_status",             # Order tracking tool call
    "confirmation",             # Handle confirmation
    "synthesize"                # Generate final response
]


# Completeness thresholds for routing
# Lowered search threshold to 0.5 - queries with product + price should search directly
COMPLETENESS_THRESHOLD_SEARCH = 0.5  # >= 50% = ready to search
COMPLETENESS_THRESHOLD_CONSULT = 0.3  # 30-50% = pre-search consultation


class LLMRouter:
    """
    Routes requests based on QueryUnderstanding output.
    
    Includes intelligent completeness checking for consultative shopping:
    - Low completeness → Ask clarifying questions
    - Medium completeness → Provide pre-search consultation
    - High completeness → Execute search
    """
    
    def _calculate_completeness(
        self,
        understanding: QueryUnderstanding,
        memory: SessionMemory
    ) -> float:
        """
        Calculate how complete the search requirements are (0.0 - 1.0).
        
        Scoring:
        - Has searchable query: 1.5 points
        - Has category: 1.0 points
        - Has gender: 0.5 points
        - Has use_case: 0.5 points
        - Has budget/price: 0.5 points
        - Has style/preference: 0.5 points
        - Has specific features: 0.5 points
        
        Max: 5.0 points → normalized to 1.0
        """
        score = 0.0
        max_score = 5.0
        
        # Check for searchable query
        if understanding.merged_search_query_en:
            query_len = len(understanding.merged_search_query_en.split())
            if query_len >= 3:
                score += 1.5  # Good query
            elif query_len >= 1:
                score += 0.8  # Basic query
        
        # Check extracted_info from understanding
        info = understanding.extracted_info or {}
        
        # Category presence
        if info.get("category") or (memory.current_intent and memory.current_intent.category):
            score += 1.0
        
        # Constraints from memory
        constraints = {}
        if memory.current_intent:
            constraints = memory.current_intent.constraints
        
        # Merge with extracted_info
        constraints.update(info)
        
        # Score individual constraints
        if constraints.get("gender"):
            score += 0.5
        if constraints.get("use_case") or constraints.get("occasion"):
            score += 0.5
        if constraints.get("price_max") or constraints.get("budget") or constraints.get("price_range"):
            score += 0.5
        if constraints.get("style") or constraints.get("preference"):
            score += 0.5
        if constraints.get("brand") or constraints.get("color") or constraints.get("size"):
            score += 0.5
        
        normalized = min(score / max_score, 1.0)
        
        logger.debug(
            f"LLMRouter: Completeness score={normalized:.2f} "
            f"(raw={score:.1f}/{max_score}, constraints={list(constraints.keys())})"
        )
        
        return normalized
    
    def route(
        self, 
        understanding: QueryUnderstanding,
        memory: SessionMemory
    ) -> RouteType:
        """
        Determine which agent/node should handle this request.
        
        For search intents, uses completeness check:
        - completeness < 0.4 → clarification (need more info)
        - completeness 0.4-0.7 → pre_search_consultation (advise first)
        - completeness > 0.7 → search (ready to search)
        
        Args:
            understanding: Output from QueryUnderstandingAgent
            memory: Current session memory
            
        Returns:
            RouteType indicating which node to execute
        """
        msg_type = understanding.message_type
        
        # Calculate completeness for search-related intents
        completeness = 0.0
        if msg_type in ("new_search", "refine_search", "unclear"):
            completeness = self._calculate_completeness(understanding, memory)
        
        logger.info(
            f"LLMRouter: Routing message_type={msg_type}, "
            f"should_search={understanding.should_search}, "
            f"merged_query='{understanding.merged_search_query_en}', "
            f"completeness={completeness:.2f}"
        )
        
        # Direct mappings (non-search intents)
        if msg_type == "greeting":
            return "greeting"
        
        if msg_type == "faq":
            return "faq"
        
        if msg_type == "order_status":
            return "order_status"
        
        if msg_type == "confirmation":
            # User confirmed → proceed to search if we have accumulated context
            if memory and memory.current_intent and memory.current_intent.is_active:
                # Check if we have enough context to search
                intent = memory.current_intent
                has_query = bool(
                    understanding.merged_search_query_en or 
                    intent.get_merged_keywords() or
                    intent.category
                )
                if has_query:
                    logger.info("LLMRouter: Confirmation with active intent → routing to search")
                    return "search"
            # No context to search - treat as unclear
            logger.info("LLMRouter: Confirmation without sufficient context → routing to clarification")
            return "clarification"
        
        # Search-related intents with completeness check
        if msg_type in ("new_search", "refine_search"):
            # AGENTIC: Check if LLM classified this as confirmation
            # (message_type should be 'confirmation' but may be misclassified)
            # If message_type is confirmation with active intent → route to search
            # Note: The LLM handles confirmation detection via prompt instructions
            
            if not understanding.merged_search_query_en:
                # No query at all → ask for clarification
                logger.info("LLMRouter: No query, routing to clarification")
                return "clarification"
            
            if completeness >= COMPLETENESS_THRESHOLD_SEARCH:
                # High completeness → ready to search
                logger.info(f"LLMRouter: High completeness ({completeness:.2f}), routing to search")
                return "search"
            elif completeness >= COMPLETENESS_THRESHOLD_CONSULT:
                # Medium completeness → pre-search consultation
                logger.info(f"LLMRouter: Medium completeness ({completeness:.2f}), routing to pre_search_consultation")
                return "pre_search_consultation"
            else:
                # Low completeness → need more info
                logger.info(f"LLMRouter: Low completeness ({completeness:.2f}), routing to clarification")
                return "clarification"
        
        # Consultation - asking about shown products
        if msg_type == "consultation":
            if memory.has_shown_products():
                return "consultation"
            else:
                # No products to discuss, redirect to clarification
                logger.warning(
                    "LLMRouter: Consultation requested but no products shown. "
                    "Redirecting to clarification."
                )
                return "clarification"
        
        # Unclear intent → check completeness
        if msg_type == "unclear":
            if completeness >= COMPLETENESS_THRESHOLD_CONSULT:
                # Some info gathered → pre-search consultation
                return "pre_search_consultation"
            return "clarification"
        
        # Fallback
        logger.warning(f"LLMRouter: Unknown message_type '{msg_type}', defaulting to clarification")
        return "clarification"
    
    def should_update_intent(self, understanding: QueryUnderstanding) -> bool:
        """Check if we should update the search intent in memory."""
        return understanding.message_type in ("new_search", "refine_search")
    
    def is_new_search(self, understanding: QueryUnderstanding) -> bool:
        """
        Check if this is a completely new search (should clear old products).
        
        AGENTIC: Uses LLM-determined message_type and is_refinement_only
        instead of hardcoded pattern matching.
        """
        if understanding.message_type != "new_search":
            return False
        
        # AGENTIC: If LLM says it's refinement-only, don't treat as new search
        if understanding.is_refinement_only:
            logger.info(f"LLMRouter: LLM detected refinement-only (is_refinement_only=True), preserving intent")
            return False
        
        # AGENTIC: If LLM classified as confirmation, don't treat as new search
        if understanding.message_type == "confirmation":
            logger.info(f"LLMRouter: Message is confirmation type, preserving intent")
            return False
        
        return True
    
    def get_completeness(
        self,
        understanding: QueryUnderstanding,
        memory: SessionMemory
    ) -> float:
        """Public method to get completeness score."""
        return self._calculate_completeness(understanding, memory)

