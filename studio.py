"""LangGraph Studio UI entrypoint for the Amazon Smart Shopping Assistant.

This module exposes the compiled graph for LangGraph Studio.
To run with LangGraph Studio:
1. Make sure you have langgraph-cli installed: pip install langgraph-cli
2. Run: langgraph dev
3. Open the URL shown in your browser (typically http://127.0.0.1:8123)
4. Enter your shopping query in the UI

The graph will process your query through these stages:
- Router: Determines the best workflow path (quick search, planning, or clarification)
- Planning: Autonomous query analysis and search planning (if needed)
- Collection: Gathers product data from Amazon via SerpAPI
- Analysis: Chain-of-thought product analysis with reasoning
- Response: Structured response generation with comprehensive insights

Example queries:
- "Find me budget-friendly wireless earbuds under $100"
- "I need a laptop for programming and video editing under $1500"
- "Best coffee makers with timer function"
- "bluetooth speaker" (triggers quick search)
"""

from __future__ import annotations

from ai_server.graphs.shopping_graph import build_graph

graph = build_graph()
__all__ = ["graph"]
