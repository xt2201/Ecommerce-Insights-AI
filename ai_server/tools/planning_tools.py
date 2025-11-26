"""Planning agent tools for query analysis and keyword expansion."""

from __future__ import annotations

import logging
from typing import Dict, Tuple

from langchain_core.tools import tool

from ai_server.llm import get_llm
from ai_server.schemas.planning_models import (
    QueryIntentAnalysis,
    ExpandedKeywords,
    QueryRequirements,
)
from ai_server.utils.prompt_loader import load_prompt


# Configure logger
logger = logging.getLogger(__name__)

# Load prompts
_PROMPTS = load_prompt("planning_agent_prompts")


def _get_prompt_section(prompt_name: str) -> str:
    """Extract specific prompt section from loaded prompts."""
    import re
    
    # Find section by name
    pattern = rf"## {prompt_name}.*?```template\n(.*?)```"
    match = re.search(pattern, _PROMPTS, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # Fallback to simple section search
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


def _get_llm():
    """Get configured LLM instance using factory pattern."""
    # Use agent-specific LLM configuration
    return get_llm(agent_name="planning")


def _extract_token_usage(raw_response) -> dict:
    """Extract token usage from LLM response."""
    tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
        tokens["input_tokens"] = raw_response.usage_metadata.get("input_tokens", 0)
        tokens["output_tokens"] = raw_response.usage_metadata.get("output_tokens", 0)
        tokens["total_tokens"] = tokens["input_tokens"] + tokens["output_tokens"]
    return tokens



@tool
def analyze_query_intent(query: str) -> Dict:
    """Analyze user query to determine shopping intent.
    
    Args:
        query: User's search query
        
    Returns:
        Dictionary with intent, specificity, requires_clarification, confidence
    """
    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(QueryIntentAnalysis, include_raw=True)
        
        prompt_template = _get_prompt_section("Analyze Query Intent Prompt")
        prompt = prompt_template.replace("{query}", query)
        
        result = structured_llm.invoke(prompt)
        analysis = result["parsed"]
        raw_response = result["raw"]
        
        # Extract and log token usage
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            input_tokens = raw_response.usage_metadata.get("input_tokens", 0)
            output_tokens = raw_response.usage_metadata.get("output_tokens", 0)
            logger.info(f"analyze_query_intent tokens: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
        
        return analysis.model_dump()
        
    except Exception as e:
        logger.warning(f"analyze_query_intent failed: {e}, using fallback")
        # Fallback to basic analysis
        return {
            "intent": "product_search",
            "specificity": 0.5,
            "requires_clarification": False,
            "confidence": 0.5
        }


@tool
def expand_keywords(query: str) -> Dict:
    """Generate alternative search keywords for better coverage.
    
    Args:
        query: Original search query
        
    Returns:
        Dictionary with keywords list
    """
    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(ExpandedKeywords, include_raw=True)
        
        prompt_template = _get_prompt_section("Expand Keywords Prompt")
        prompt = prompt_template.replace("{query}", query)
        
        result = structured_llm.invoke(prompt)
        keywords = result["parsed"]
        raw_response = result["raw"]
        
        # Extract and log token usage
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            input_tokens = raw_response.usage_metadata.get("input_tokens", 0)
            output_tokens = raw_response.usage_metadata.get("output_tokens", 0)
            logger.info(f"expand_keywords tokens: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
        
        return keywords.model_dump()
        
    except Exception as e:
        logger.warning(f"expand_keywords failed: {e}, using fallback")
        # Fallback: use original query
        return {"keywords": [query]}


@tool
def extract_requirements(query: str) -> Dict:
    """Extract specific requirements from query.
    
    Args:
        query: User's search query
        
    Returns:
        Dictionary with max_price, min_rating, required_features, brand_preferences
    """
    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(QueryRequirements, include_raw=True)
        
        prompt_template = _get_prompt_section("Extract Requirements Prompt")
        prompt = prompt_template.replace("{query}", query)
        
        result = structured_llm.invoke(prompt)
        requirements = result["parsed"]
        raw_response = result["raw"]
        
        # Extract and log token usage
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            input_tokens = raw_response.usage_metadata.get("input_tokens", 0)
            output_tokens = raw_response.usage_metadata.get("output_tokens", 0)
            logger.info(f"extract_requirements tokens: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
        
        # Check if parsed result is valid
        if requirements is None:
            logger.warning("extract_requirements returned None, using fallback")
            return {
                "max_price": None,
                "min_rating": None,
                "required_features": [],
                "brand_preferences": []
            }
        
        return requirements.model_dump()
        
    except Exception as e:
        logger.warning(f"extract_requirements failed: {e}, using fallback")
        # Fallback: no requirements
        return {
            "max_price": None,
            "min_rating": None,
            "required_features": [],
            "brand_preferences": []
        }


@tool
def generate_comprehensive_plan(query: str) -> Dict:
    """Generate a comprehensive search plan in a single step.
    
    Combines intent analysis, keyword expansion, and requirement extraction.
    
    Args:
        query: User's search query
        
    Returns:
        Dictionary matching ComprehensiveSearchPlan schema
    """
    try:
        from ai_server.schemas.planning_models import ComprehensiveSearchPlan
        
        llm = _get_llm()
        structured_llm = llm.with_structured_output(ComprehensiveSearchPlan, include_raw=True)
        
        prompt_template = _get_prompt_section("Comprehensive Search Plan Prompt")
        prompt = prompt_template.replace("{query}", query)
        
        result = structured_llm.invoke(prompt)
        plan = result["parsed"]
        raw_response = result["raw"]
        
        # Extract and log token usage
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            input_tokens = raw_response.usage_metadata.get("input_tokens", 0)
            output_tokens = raw_response.usage_metadata.get("output_tokens", 0)
            logger.info(f"generate_comprehensive_plan tokens: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
        
        return plan.model_dump()
        
    except Exception as e:
        logger.warning(f"generate_comprehensive_plan failed: {e}, using fallback")
        # Fallback to basic plan
        return {
            "intent_analysis": {
                "intent": "product_search",
                "specificity": 0.5,
                "requires_clarification": False,
                "confidence": 0.5
            },
            "keywords": [query],
            "requirements": {
                "max_price": None,
                "min_rating": None,
                "required_features": [],
                "brand_preferences": []
            },
            "reasoning": "Fallback due to error"
        }


def generate_comprehensive_plan_with_tokens(query: str) -> Tuple[Dict, Dict]:
    """Generate comprehensive plan and return with token usage.
    
    This is the non-tool version that returns both plan and token dict.
    Use this when you need to track token usage (e.g., in planning_agent).
    
    Args:
        query: User's search query
        
    Returns:
        Tuple of (plan_dict, token_dict)
    """
    tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    try:
        from ai_server.schemas.planning_models import ComprehensiveSearchPlan
        
        llm = _get_llm()
        structured_llm = llm.with_structured_output(ComprehensiveSearchPlan, include_raw=True)
        
        prompt_template = _get_prompt_section("Comprehensive Search Plan Prompt")
        prompt = prompt_template.replace("{query}", query)
        
        result = structured_llm.invoke(prompt)
        plan = result["parsed"]
        raw_response = result["raw"]
        
        # Extract token usage
        tokens = _extract_token_usage(raw_response)
        logger.info(f"generate_comprehensive_plan tokens: {tokens['input_tokens']} input + {tokens['output_tokens']} output = {tokens['total_tokens']} total")
        
        return plan.model_dump(), tokens
        
    except Exception as e:
        logger.warning(f"generate_comprehensive_plan failed: {e}, using fallback")
        # Fallback to basic plan
        return {
            "intent_analysis": {
                "intent": "product_search",
                "specificity": 0.5,
                "requires_clarification": False,
                "confidence": 0.5
            },
            "keywords": [query],
            "requirements": {
                "max_price": None,
                "min_rating": None,
                "required_features": [],
                "brand_preferences": []
            },
            "reasoning": "Fallback due to error"
        }, tokens
