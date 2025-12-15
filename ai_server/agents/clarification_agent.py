"""
Clarification Agent

LLM-powered agent that generates context-aware clarification questions.
Replaces hardcoded question templates.
"""
from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.schemas.session_memory import SessionMemory
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


class ClarificationResult(BaseModel):
    """Result from clarification agent."""
    questions: List[str] = Field(default_factory=list)
    priority_info_needed: str = "general"
    reasoning: str = ""


class ClarificationAgent:
    """
    LLM-powered clarification question generator.
    
    Instead of fixed question templates, uses LLM to generate
    context-aware questions based on what's already known.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="manager")
        try:
            self.prompts = load_prompts_as_dict("clarification_prompts")
        except Exception as e:
            logger.warning(f"ClarificationAgent: Failed to load prompts: {e}")
            self.prompts = {}
    
    def generate_questions(
        self, 
        memory: SessionMemory,
        user_message: str = ""
    ) -> ClarificationResult:
        """
        Generate context-aware clarification questions.
        
        Args:
            memory: Current session memory with intent
            user_message: The unclear user message
            
        Returns:
            ClarificationResult with questions
        """
        logger.info("ClarificationAgent: Generating clarification questions")
        
        # Build context for LLM
        original_query = ""
        category = "unknown"
        constraints = {}
        known_info = []
        missing_info = []
        
        if memory.current_intent:
            original_query = memory.current_intent.original_query or user_message
            category = memory.current_intent.category or "unknown"
            constraints = memory.current_intent.constraints
            
            # What we know
            if category != "unknown":
                known_info.append(f"Category: {category}")
            for key, value in constraints.items():
                if value:
                    known_info.append(f"{key}: {value}")
            
            # What's missing (common attributes)
            if not constraints.get("gender"):
                missing_info.append("gender (male/female)")
            if not constraints.get("use_case"):
                missing_info.append("use case (casual/sports/formal)")
            if not constraints.get("price_max"):
                missing_info.append("budget")
        else:
            original_query = user_message
            missing_info = ["product type", "category", "preferences"]
        
        # Get prompts
        system_prompt = self.prompts.get("system_prompt", self._default_system_prompt())
        user_template = self.prompts.get("user_prompt_template", self._default_user_template())
        
        # Fill template
        user_prompt = user_template.format(
            original_query=original_query,
            category=category,
            constraints=json.dumps(constraints) if constraints else "{}",
            known_info="\n".join(f"- {info}" for info in known_info) if known_info else "Nothing specific",
            missing_info=", ".join(missing_info) if missing_info else "Nothing critical"
        )
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Clean response
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed = json.loads(content)
            
            result = ClarificationResult(
                questions=parsed.get("questions", []),
                priority_info_needed=parsed.get("priority_info_needed", "general"),
                reasoning=parsed.get("reasoning", "")
            )
            
            logger.info(f"ClarificationAgent: Generated {len(result.questions)} questions")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"ClarificationAgent: JSON parse error: {e}")
            return self._fallback_questions(memory)
        except Exception as e:
            logger.error(f"ClarificationAgent: Error: {e}")
            return self._fallback_questions(memory)
    
    def _fallback_questions(self, memory: SessionMemory) -> ClarificationResult:
        """Fallback when LLM fails."""
        logger.warning("ClarificationAgent: Using fallback questions")
        
        # Use prompts file fallback or defaults
        fallback = self.prompts.get("fallback_questions", {})
        
        questions = []
        if not memory.current_intent:
            questions.append(fallback.get("no_category", "What type of product are you looking for?"))
        else:
            if not memory.current_intent.constraints.get("gender"):
                questions.append(fallback.get("no_gender", "Is this for men or women?"))
            if not memory.current_intent.constraints.get("use_case"):
                questions.append(fallback.get("no_use_case", "What will you use it for?"))
        
        return ClarificationResult(
            questions=questions[:3],
            priority_info_needed="general",
            reasoning="Fallback questions used"
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an AI Shopping Assistant that needs more information to help the customer.
Generate 2-3 clarification questions based on what's missing.
Ask in the same language as the customer's query.
Output JSON: {"questions": [...], "priority_info_needed": "...", "reasoning": "..."}"""
    
    def _default_user_template(self) -> str:
        return """Customer query: "{original_query}"
Category: {category}
Known: {known_info}
Missing: {missing_info}

Generate clarification questions. Output JSON only."""


# Singleton
_clarification_agent: Optional[ClarificationAgent] = None


def get_clarification_agent() -> ClarificationAgent:
    """Get the singleton clarification agent."""
    global _clarification_agent
    if _clarification_agent is None:
        _clarification_agent = ClarificationAgent()
    return _clarification_agent
