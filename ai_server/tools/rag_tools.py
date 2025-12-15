from __future__ import annotations

import logging
from langchain_core.tools import tool
from ai_server.rag.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

# Initialize Knowledge Base (Singleton-ish)
_kb = None

def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
        _kb.initialize()
    return _kb


@tool
def lookup_policy_tool(query: str) -> str:
    """
    Search for return policies, shipping info, and other store policies.
    Use this when the user asks about returns, shipping, or store policies.
    
    Args:
        query: The user's question about policies
    """
    kb = get_kb()
    result = kb.query(query, k=2, filter_metadata={"type": "policy"})
    if not result:
        result = kb.query(query, k=2)
    return result if result else "No specific policy found for your query."


@tool
def lookup_faq_tool(query: str) -> str:
    """
    Search for frequently asked questions about payment, warranty, etc.
    Use this when the user asks about common questions, warranty, or payment.
    
    Args:
        query: The user's FAQ question
    """
    kb = get_kb()
    result = kb.query(query, k=2, filter_metadata={"type": "faq"})
    if not result:
        result = kb.query(query, k=2)
    return result if result else "No FAQ found for your query."


# Export LangChain tools list
RAG_TOOLS = [lookup_policy_tool, lookup_faq_tool]
