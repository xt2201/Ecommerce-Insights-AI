"""
Response Generator Module
Handles all final response generation and synthesis.
Separated from ManagerAgent for better maintainability.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.shared_workspace import SharedWorkspace
# from ai_server.agents.intent_classifier import IntentClassifier  # DEPRECATED

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Handles final response generation.
    Separated from orchestration logic for single responsibility.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="manager")
        # self.intent_classifier = IntentClassifier()  # DEPRECATED
    
    def generate(self, workspace: SharedWorkspace) -> Dict[str, Any]:
        """
        Generate final response based on workspace state and intent.
        Returns: dict with 'content', 'type', and optionally 'summary', 'follow_up_suggestions'
        """
        # Check for tool output first
        if "tool_output" in workspace.artifacts:
            return self._generate_tool_response(workspace)
        
        # Classify intent (DEPRECATED - now handled by Graph)
        # intent = self.intent_classifier.classify(workspace.goal)
        
        # Route to appropriate generator
        # if intent == "greeting":
        #    return self._generate_greeting(workspace)

        
        # Check for candidates
        valid_candidates = [c for c in workspace.candidates if c.status in ["approved", "reviewed"]]
        
        if valid_candidates:
            return self._generate_product_report(workspace, valid_candidates)
        
        # Fallback: general response
        return self._generate_fallback(workspace)
    
    def _generate_greeting(self, workspace: SharedWorkspace) -> Dict[str, Any]:
        """Generate friendly greeting response."""
        prompt = (
            f"You are a friendly AI Shopping Assistant named Qwen. The user said: '{workspace.goal}'\n\n"
            f"Respond naturally and helpfully. If they're greeting you, introduce yourself briefly.\n"
            f"If they're asking what you can do, explain your capabilities (product search, comparisons, recommendations).\n"
            f"Keep it concise and friendly. Use markdown for formatting.\n"
            f"DO NOT generate any product recommendations or 'Top Pick' sections.\n"
            f"Response (Markdown):"
        )
        
        content = self._invoke_llm(prompt)
        
        return {
            "content": content,
            "type": "informational_response",
            "summary": "Greeting response"
        }
    
    def _generate_tool_response(self, workspace: SharedWorkspace) -> Dict[str, Any]:
        """Generate response based on tool output."""
        tool_output = workspace.artifacts.get("tool_output", "")
        
        return {
            "content": f"Here is the information I found regarding your request:\n\n{tool_output}",
            "type": "informational_response",
            "summary": "Tool-based response"
        }
    
    def _generate_product_report(self, workspace: SharedWorkspace, candidates: list) -> Dict[str, Any]:
        """Generate product recommendation report."""
        # Sort by domain score
        try:
            candidates.sort(key=lambda x: float(x.domain_score or 0.0), reverse=True)
        except Exception:
            pass
        
        top_picks = candidates[:5]
        
        # Build candidates string
        candidates_str = "\n".join([
            f"- {c.title} (Price: {c.price}, Quality: {c.quality_score}, Relevance: {c.domain_score})\n  Reason: {c.notes}"
            for c in top_picks
        ])
        
        prompt = (
            f"You are an expert Shopping Assistant. Create a final markdown report for the user based on these top candidates:\n\n"
            f"{candidates_str}\n\n"
            f"User Goal: {workspace.goal}\n\n"
            f"Requirements:\n"
            f"1. Start with a friendly summary.\n"
            f"2. Present the top recommendation clearly with '## Top Pick due to...'.\n"
            f"3. Compare the alternatives in a table or bullet points.\n"
            f"4. Mention any trade-offs.\n"
            f"Content (Markdown):"
        )
        
        content = self._invoke_llm(prompt)
        
        # Generate follow-up suggestions
        suggestions = self._generate_follow_ups(workspace, top_picks)
        
        return {
            "content": content,
            "type": "recommendation_report",
            "summary": f"Found {len(top_picks)} top recommendations",
            "follow_up_suggestions": suggestions
        }
    
    def _generate_fallback(self, workspace: SharedWorkspace) -> Dict[str, Any]:
        """Generate fallback response when no specific content available."""
        prompt = (
            f"You are a helpful AI Shopping Assistant. The user asked: '{workspace.goal}'\n\n"
            f"We couldn't find specific products matching their request. "
            f"Provide a helpful response suggesting how they might refine their search or what alternatives they could consider.\n"
            f"Keep it concise and friendly. Use markdown.\n"
            f"Response:"
        )
        
        content = self._invoke_llm(prompt)
        
        return {
            "content": content,
            "type": "informational_response",
            "summary": "Fallback response"
        }
    
    def _generate_follow_ups(self, workspace: SharedWorkspace, top_picks: list) -> list:
        """Generate follow-up suggestions."""
        try:
            picks_str = ", ".join([c.title for c in top_picks[:3]])
            prompt = (
                f"Based on the user's query: '{workspace.goal}' and top products: {picks_str}\n\n"
                f"Generate 3 short, helpful follow-up questions the user might ask next. "
                f"Be specific and contextual. Output as a JSON array of strings only, no explanation."
            )
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Clean <think> blocks
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            # Parse JSON
            import json
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"Failed to generate follow-ups: {e}")
        
        return []
    
    def _invoke_llm(self, prompt: str) -> str:
        """Invoke LLM and clean response."""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Clean <think> blocks
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            # Strip markdown code fences
            content = re.sub(r'^```(?:markdown|md)?\s*\n?', '', content.strip())
            content = re.sub(r'\n?```\s*$', '', content.strip())
            
            return content
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            return f"I apologize, but I encountered an error processing your request."
