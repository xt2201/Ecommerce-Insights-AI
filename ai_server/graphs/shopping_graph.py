"""LangGraph workflow with autonomous agents and conditional routing."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from ai_server.agents.analysis_agent import analyze_products
from ai_server.agents.collection_agent import collect_products
from ai_server.agents.planning_agent import plan_search
from ai_server.agents.response_agent import generate_response
from ai_server.agents.router_agent import (
    quick_search_handler,
    request_clarification_handler,
    route_query,
    router_node,
)
from ai_server.agents.review_agent import analyze_reviews
from ai_server.agents.market_agent import analyze_market
from ai_server.agents.price_agent import analyze_prices
from ai_server.core.telemetry import traceable_node
from ai_server.schemas.agent_state import AgentState

def build_graph():
    """Build graph with autonomous agents and conditional routing.
    
    Architecture:
                        ┌─────────────┐
                        │   Router    │
                        └──────┬──────┘
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ Quick Search │   │  Planning    │   │Clarification │
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
           │                  │                  │
           └────────►  Collection  ◄─────────────┘
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
        ┌──────────────┐       ┌──────────────┐
        │ Review Intel │       │ Market Intel │
        └──────┬───────┘       └──────┬───────┘
               │                      │
               ▼                      ▼
        ┌─────────────────────────────────────┐
        │           Price Tracking            │
        └──────────────────┬──────────────────┘
                           │
                           ▼
                        Analysis
                           │
                         Response
    """
    
    graph = StateGraph(AgentState)
    
    # Add router node (entry point)
    graph.add_node("router", traceable_node("Router", router_node))
    
    # Add workflow nodes
    graph.add_node("quick_search", traceable_node("QuickSearch", quick_search_handler))
    graph.add_node("clarification", traceable_node("Clarification", request_clarification_handler))
    graph.add_node("planning", traceable_node("Planning", plan_search))
    graph.add_node("collection", traceable_node("Collection", collect_products))
    
    # New Intelligence Nodes
    graph.add_node("review_intelligence", traceable_node("ReviewIntel", analyze_reviews))
    graph.add_node("market_intelligence", traceable_node("MarketIntel", analyze_market))
    graph.add_node("price_tracking", traceable_node("PriceTracking", analyze_prices))
    
    graph.add_node("analysis", traceable_node("Analysis", analyze_products))
    graph.add_node("response", traceable_node("Response", generate_response))
    
    # Set entry point
    graph.set_entry_point("router")
    
    # Conditional routing from router
    graph.add_conditional_edges(
        "router",
        route_query,
        {
            "direct_search": "quick_search",
            "planning": "planning",
            "clarification": "clarification"
        }
    )
    
    # Quick search path: router → quick_search → collection
    graph.add_edge("quick_search", "collection")
    
    # Planning path: router → planning → collection
    graph.add_edge("planning", "collection")
    
    # Clarification path: router → clarification → END (stop here)
    graph.add_edge("clarification", END)
    
    # Collection branches to Intelligence nodes (Parallel)
    # Flow: Collection -> [Review, Market, Price] -> Analysis
    
    graph.add_edge("collection", "review_intelligence")
    graph.add_edge("collection", "market_intelligence")
    graph.add_edge("collection", "price_tracking")
    
    # Converge to Analysis
    graph.add_edge("review_intelligence", "analysis")
    graph.add_edge("market_intelligence", "analysis")
    graph.add_edge("price_tracking", "analysis")
    
    graph.add_edge("analysis", "response")
    graph.add_edge("response", END)
    
    return graph.compile()

# Export compiled graph
graph = build_graph()
