"""LangGraph Studio UI entrypoint for the Amazon Smart Shopping Assistant.

This module exposes the compiled graph for LangGraph Studio.
To run with LangGraph Studio:
1. Make sure you have langgraph-cli installed: pip install langgraph-cli
2. Run: langgraph dev OR ./run_langgraph.sh
3. Open the URL shown in your browser (typically http://127.0.0.1:8123)
4. Enter your shopping query in the UI

V7 Architecture (100% Agentic + Session Persistence):
- QueryUnderstandingAgent: LLM-powered intent detection with full context
- LLMRouter: Routes based on completeness score (clarify/consult/search)
- SessionManager: Persists conversation across requests (SQLite)
- Pattern Detection: Vietnamese refinement fallback ("giới tính", "màu", "giá")

Example queries:
- "tôi muốn mua giày sneaker cho chạy bộ" (Vietnamese supported)
- "Find me budget-friendly wireless earbuds under $100"
- "Best coffee makers with timer function"
"""

from __future__ import annotations

from ai_server.graphs.shopping_graph import build_graph

graph = build_graph()
__all__ = ["graph"]
