"""
RAG (Retrieval Augmented Generation) Module

Provides:
- KnowledgeBase: FAISS-backed semantic search for policies and FAQs
- KnowledgeGraph: Entity storage with relationship linking
- EntityExtractor: LLM-powered entity extraction from text

Usage:
    from ai_server.rag import get_knowledge_base, get_knowledge_graph

    kb = get_knowledge_base()
    kb.initialize()
    context = kb.query("How do I return an item?")

    kg = get_knowledge_graph()
    context = kg.get_entity_context("return policy")
"""

from ai_server.rag.knowledge_base import KnowledgeBase, get_knowledge_base
from ai_server.rag.knowledge_graph import KnowledgeGraph, get_knowledge_graph
from ai_server.rag.entity_extractor import EntityExtractor, get_entity_extractor

__all__ = [
    "KnowledgeBase",
    "get_knowledge_base",
    "KnowledgeGraph", 
    "get_knowledge_graph",
    "EntityExtractor",
    "get_entity_extractor",
]
