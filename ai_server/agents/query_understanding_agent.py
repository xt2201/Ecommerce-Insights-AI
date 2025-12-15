"""
Query Understanding Agent

LLM-powered agent that analyzes user messages in the context of
the full conversation history. Key innovation: understands whether
a message is a NEW search, REFINEMENT, or CONSULTATION.
"""
from __future__ import annotations

import logging
import json
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.session_memory import SessionMemory, SearchIntent, ShownProduct
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


class QueryUnderstanding(BaseModel):
    """
    Structured understanding of user's message in conversation context.
    
    This is the output of the QueryUnderstandingAgent - a rich analysis
    that tells downstream agents exactly what to do.
    """
    # Classification
    message_type: Literal[
        "new_search",      # Starting a fresh search
        "refine_search",   # Refining/constraining previous search
        "consultation",    # Asking about shown products
        "greeting",        # Hello/intro
        "faq",             # Policy questions
        "order_status",    # Order tracking
        "confirmation",    # Yes/OK response
        "unclear"          # Need clarification
    ]
    
    # AGENTIC: LLM determines if message only contains constraints without new product category
    # This replaces hardcoded pattern matching with LLM reasoning
    is_refinement_only: bool = False
    
    # Reasoning (for debugging/transparency)
    reasoning: str = ""
    
    # Extracted information from current message
    extracted_info: Dict[str, Any] = Field(default_factory=dict)
    # Example: {
    #   "category": "shoes",
    #   "gender": "female",
    #   "use_case": "running",
    #   "color": "white"
    # }
    
    # For search intents
    merged_search_query_en: Optional[str] = None  # English query for Amazon
    merged_search_query_vi: Optional[str] = None  # Vietnamese for display
    should_search: bool = False
    
    # For consultation
    consultation_question: Optional[str] = None
    consultation_type: Optional[str] = None  # "price_compare", "recommendation", "general"
    
    # Confidence
    confidence: float = 0.8



class QueryUnderstandingAgent:
    """
    LLM-powered query understanding with full conversation context.
    
    This agent is the "brain" that understands user intent by seeing:
    - What user previously searched for
    - What products were shown
    - The conversation history
    
    It outputs a structured QueryUnderstanding that tells other agents
    exactly what to do.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="manager")
        
        # Load prompts from external file
        try:
            from ai_server.utils.prompt_loader import load_prompts_as_dict
            self.prompts = load_prompts_as_dict("query_understanding_prompts")
        except Exception as e:
            logger.warning(f"QueryUnderstandingAgent: Failed to load prompts: {e}")
            self.prompts = {}
    
    def _get_system_prompt(self) -> str:
        """Get system prompt from external file or fallback to default."""
        if self.prompts and "system_prompt" in self.prompts:
            return self.prompts["system_prompt"]
        
        # Fallback default prompt (should not be used in production)
        return """You are analyzing a user message in an ongoing shopping conversation.
Understand the user's intent by considering the full conversation context.

Message types: new_search, refine_search, consultation, greeting, faq, order_status, confirmation, unclear

Output JSON with: message_type, reasoning, extracted_info, merged_search_query_en, should_search, confidence"""
    
    def understand(
        self, 
        message: str, 
        memory: SessionMemory
    ) -> QueryUnderstanding:
        """
        Analyze user message with full conversation context.
        
        Args:
            message: User's current message
            memory: Full session memory with intent, products, history
            
        Returns:
            QueryUnderstanding with structured analysis
        """
        logger.info(f"QueryUnderstandingAgent: Analyzing '{message[:50]}...'")
        
        # Build context string
        context_str = self._build_context(memory)
        
        # Build user prompt
        user_prompt = f"""## Session Context
{context_str}

## User's New Message
"{message}"

Analyze this message and output JSON only."""
        
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Clean response
            content = self._clean_response(content)
            
            # Parse JSON
            parsed = json.loads(content)
            
            understanding = QueryUnderstanding(
                message_type=parsed.get("message_type", "unclear"),
                reasoning=parsed.get("reasoning", ""),
                extracted_info=parsed.get("extracted_info", {}),
                merged_search_query_en=parsed.get("merged_search_query_en"),
                merged_search_query_vi=parsed.get("merged_search_query_vi"),
                should_search=parsed.get("should_search", False),
                consultation_question=parsed.get("consultation_question"),
                consultation_type=parsed.get("consultation_type"),
                confidence=parsed.get("confidence", 0.8)
            )
            
            # AGENTIC: Check if short message might be confirmation when we have active intent
            if (understanding.message_type == "new_search" and 
                len(message.split()) <= 5 and
                memory and memory.current_intent and memory.current_intent.is_active):
                # Use LLM to check if this is actually a confirmation
                if self._is_confirmation_intent(message, memory):
                    logger.info("QueryUnderstandingAgent: Detected confirmation pattern, updating type")
                    understanding.message_type = "confirmation"
                    understanding.should_search = True
                    # Keep merged_query from memory's intent
                    if memory.current_intent:
                        keywords = memory.current_intent.get_merged_keywords()
                        category = memory.current_intent.category or ""
                        understanding.merged_search_query_en = f"{category} {keywords}".strip()
            
            if understanding.message_type == "unclear":
                # If LLM says unclear, try fallback heuristics to see if it's actually a simple search
                fallback = self._fallback_understanding(message, memory)
                if fallback.message_type == "new_search":
                    logger.info("QueryUnderstandingAgent: Overriding 'unclear' with fallback 'new_search'")
                    return fallback
                    
            logger.info(
                f"QueryUnderstandingAgent: type={understanding.message_type}, "
                f"merged_query={understanding.merged_search_query_en}"
            )
            
            return understanding
            
        except json.JSONDecodeError as e:
            logger.error(f"QueryUnderstandingAgent: JSON parse error: {e}")
            return self._fallback_understanding(message, memory)
        except Exception as e:
            logger.error(f"QueryUnderstandingAgent: Error: {e}")
            return self._fallback_understanding(message, memory)
    
    def _build_context(self, memory: SessionMemory) -> str:
        """Build context string for LLM."""
        sections = []
        
        # Current search intent
        if memory.current_intent and memory.current_intent.is_active:
            sections.append("### Current Search Intent")
            sections.append(f"Original query: \"{memory.current_intent.original_query}\"")
            if memory.current_intent.category:
                sections.append(f"Category: {memory.current_intent.category}")
            if memory.current_intent.constraints:
                constraints = ", ".join(
                    f"{k}={v}" for k, v in memory.current_intent.constraints.items()
                )
                sections.append(f"Constraints: {constraints}")
            if memory.current_intent.refinements:
                sections.append(f"Previous refinements: {memory.current_intent.refinements}")
        else:
            sections.append("### No active search intent (this is a new conversation)")
        
        # Products shown
        if memory.shown_products:
            sections.append("\n### Products Already Shown to User")
            for i, p in enumerate(memory.shown_products[:5], 1):
                price_str = f"${p.price}" if p.price else "price unknown"
                sections.append(f"{i}. {p.title} ({price_str})")
        else:
            sections.append("\n### No products shown yet")
        
        # Recent conversation
        if memory.turns:
            sections.append("\n### Recent Conversation")
            for turn in memory.get_recent_turns(4):
                role = "User" if turn.role == "user" else "Assistant"
                content = turn.content[:80] + "..." if len(turn.content) > 80 else turn.content
                sections.append(f"{role}: {content}")
        
        return "\n".join(sections)
    
    def _clean_response(self, content: str) -> str:
        """Clean LLM response for JSON parsing."""
        # Remove <think> blocks
        if "<think>" in content:
            content = content.split("</think>")[-1].strip()
        
        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return content
    
    def _fallback_understanding(
        self, 
        message: str, 
        memory: SessionMemory
    ) -> QueryUnderstanding:
        """Simple fallback when LLM fails."""
        logger.warning("QueryUnderstandingAgent: Using fallback understanding")
        
        message_lower = message.lower()
        
        # Simple heuristics
        if any(kw in message_lower for kw in ["hello", "hi", "chào", "xin chào"]):
            return QueryUnderstanding(message_type="greeting", confidence=0.6)
        
        if memory.shown_products and any(kw in message_lower for kw in [
            "nào", "which", "rẻ", "cheap", "tốt", "best", "so sánh", "compare"
        ]):
            return QueryUnderstanding(
                message_type="consultation",
                consultation_question=message,
                confidence=0.5
            )
        
        # Default to new search
        return QueryUnderstanding(
            message_type="new_search",
            merged_search_query_en=message,
            should_search=True,
            confidence=0.4
        )
    
    def _is_confirmation_intent(self, message: str, memory: SessionMemory) -> bool:
        """
        Use LLM to determine if a short message is actually a confirmation to proceed.
        
        This is called when a short message was classified as new_search but we have
        active search context. The LLM decides if the user meant "go ahead with the search".
        
        Agentic approach: Uses LLM reasoning instead of hardcoded patterns.
        """
        try:
            # Build context for LLM
            accumulated_query = ""
            if memory.current_intent:
                keywords = memory.current_intent.get_merged_keywords()
                category = memory.current_intent.category or ""
                accumulated_query = f"{category} {keywords}".strip()
            
            prompt = f"""You are analyzing if a user message is a CONFIRMATION to proceed with a search.

Current search context:
- Accumulated query: "{accumulated_query}"
- User has been building up search criteria in previous turns

User's short message: "{message}"

Is this user message a CONFIRMATION to proceed with the search?
Examples of confirmations:
- "ok", "yes", "go ahead", "search now", "find it"
- Vietnamese: "tìm đi", "ok tìm giúp tôi", "tìm luôn", "được", "ừ", "tốt"

Answer with ONLY "yes" or "no"."""

            response = self.llm.invoke([HumanMessage(content=prompt)])
            answer = response.content.strip().lower()
            
            # Clean think blocks
            if "<think>" in answer:
                answer = answer.split("</think>")[-1].strip()
            
            is_confirmation = answer.startswith("yes") or "yes" in answer[:10]
            
            if is_confirmation:
                logger.info(f"QueryUnderstandingAgent: LLM detected '{message}' as confirmation")
            
            return is_confirmation
            
        except Exception as e:
            logger.warning(f"QueryUnderstandingAgent: _is_confirmation_intent failed: {e}")
            return False
