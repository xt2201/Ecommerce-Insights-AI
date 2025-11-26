"""Token usage tracking utilities for LLM calls.

Provides helpers to extract actual token counts from LangChain LLM responses.
Based on TOKEN_COUNTER.MD guide for accurate token counting with structured outputs.
"""

from __future__ import annotations

from typing import Any, Optional
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult


def extract_token_usage(raw_msg: Any) -> dict[str, int]:
    """Extract token usage from LLM response (chuẩn hóa theo TOKEN_COUNTER.MD).
    
    Hỗ trợ:
    - AIMessage với response_metadata
    - Dict từ include_raw=True (out["raw"])
    - LLMResult với llm_output
    
    Args:
        raw_msg: LLM response (AIMessage, dict, hoặc LLMResult)
        
    Returns:
        Dict với input_tokens, output_tokens, total_tokens
    """
    # Default values
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0
    }
    
    # Case 1: Dict với "raw" key (từ include_raw=True)
    if isinstance(raw_msg, dict) and "raw" in raw_msg:
        raw_msg = raw_msg["raw"]  # Unwrap to AIMessage
    
    # Case 2: AIMessage hoặc object có response_metadata
    if hasattr(raw_msg, "response_metadata"):
        md = raw_msg.response_metadata or {}
        
        # Trường hợp 2.1: 'token_usage' (Cerebras, OpenAI)
        tu = md.get("token_usage")
        if isinstance(tu, dict):
            input_tokens = tu.get("prompt_tokens")
            output_tokens = tu.get("completion_tokens")
            total_tokens = tu.get("total_tokens")
            
            usage["input_tokens"] = input_tokens or 0
            usage["output_tokens"] = output_tokens or 0
            usage["total_tokens"] = total_tokens or (
                (input_tokens or 0) + (output_tokens or 0)
            )
            return usage
        
        # Trường hợp 2.2: 'usage_metadata' (Gemini, mới hơn)
        um = md.get("usage_metadata")
        if isinstance(um, dict):
            input_tokens = um.get("input_tokens") or um.get("prompt_tokens")
            output_tokens = um.get("output_tokens") or um.get("completion_tokens")
            total_tokens = um.get("total_tokens")
            
            usage["input_tokens"] = input_tokens or 0
            usage["output_tokens"] = output_tokens or 0
            usage["total_tokens"] = total_tokens or (
                (input_tokens or 0) + (output_tokens or 0)
            )
            return usage
    
    # Case 3: AIMessage.usage_metadata trực tiếp (LangChain mới)
    if hasattr(raw_msg, 'usage_metadata') and raw_msg.usage_metadata:
        metadata = raw_msg.usage_metadata
        input_tokens = metadata.get("input_tokens") or metadata.get("prompt_tokens")
        output_tokens = metadata.get("output_tokens") or metadata.get("completion_tokens")
        total_tokens = metadata.get("total_tokens")
        
        usage["input_tokens"] = input_tokens or 0
        usage["output_tokens"] = output_tokens or 0
        usage["total_tokens"] = total_tokens or (
            (input_tokens or 0) + (output_tokens or 0)
        )
        return usage
    
    # Case 4: LLMResult với llm_output
    if isinstance(raw_msg, LLMResult) and hasattr(raw_msg, 'llm_output'):
        llm_output = raw_msg.llm_output or {}
        token_usage = llm_output.get('token_usage', {})
        if token_usage:
            usage["input_tokens"] = token_usage.get("prompt_tokens", 0)
            usage["output_tokens"] = token_usage.get("completion_tokens", 0)
            usage["total_tokens"] = token_usage.get("total_tokens", 0)
            return usage
    
    # Return zeros if no usage found
    return usage
