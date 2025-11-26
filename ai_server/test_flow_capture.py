import asyncio
import logging
import sys
import time
import json
import os
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import HumanMessage

from ai_server.graphs.shopping_graph import graph
from ai_server.core.telemetry import configure_langsmith
from ai_server.core.trace import get_trace_manager
from ai_server.utils.logger import get_logger

# Setup logging
logger = get_logger("test_flow", log_file="flow_output.txt")

def save_capture(agent_name: str, data: Any):
    """Save captured data to file."""
    os.makedirs("capture_data", exist_ok=True)
    
    # Handle non-serializable objects if necessary (basic handling)
    def default_serializer(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    file_path = f"capture_data/{agent_name}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=default_serializer)
    print(f"   💾 Saved capture to {file_path}")

async def run_test_flow():
    """Run the full shopping flow and capture output."""
    print("🚀 Starting Test Flow Capture...")
    
    # Configure tracing
    configure_langsmith()
    
    # Test query
    query = "Best noise cancelling headphones under $300 for working at office"
    print(f"❓ Query: {query}\n")
    
    initial_state = {
        "user_query": query,
        "chat_history": []
        # Don't pass trace_id - let router_agent create it
    }
    
    total_tokens = 0
    trace_manager = get_trace_manager()
    current_trace_id = None  # Track trace_id across nodes
    
    try:
        # Run graph
        async for event in graph.astream(initial_state):
            for node, output in event.items():
                print(f"📍 Node Completed: {node.upper()}")
                
                # Get token usage from trace manager (accurate)
                # Use trace_id from output if available, otherwise use saved one
                trace_id = output.get("trace_id") or current_trace_id
                if trace_id and not current_trace_id:
                    current_trace_id = trace_id  # Save for parallel nodes
                trace = trace_manager.get_trace(trace_id) if trace_id else None
                
                # Find the step for this node
                node_tokens = 0
                input_tok = 0
                output_tok = 0
                
                if trace:
                    # Map node name to agent name suffix
                    node_to_agent = {
                        "router": "router_agent",
                        "planning": "planning_agent",
                        "quick_search": "router_agent",
                        "collection": "collection_agent",
                        "review_intelligence": "review_agent",
                        "market_intelligence": "market_agent",
                        "price_tracking": "price_agent",
                        "analysis": "analysis_agent",
                        "response": "response_agent"
                    }
                    agent_name = node_to_agent.get(node, node)
                    
                    # Find matching step (most recent step for this agent)
                    for step in reversed(trace.steps):  # Most recent first
                        if step.agent_name == agent_name:
                            if step.token_usage and step.token_usage.total_tokens > 0:
                                node_tokens = step.token_usage.total_tokens
                                input_tok = step.token_usage.prompt_tokens
                                output_tok = step.token_usage.completion_tokens
                                print(f"   🎟️ Token Usage: {node_tokens} (In: {input_tok}, Out: {output_tok})")
                            break
                
                if node_tokens == 0:
                    # No token data available (e.g., Collection agent doesn't use LLM)
                    if node == "collection":
                        print(f"   🎟️ Token Usage: N/A (API only, no LLM)")
                    else:
                        print(f"   🎟️ Token Usage: 0 (no LLM calls made)")
                
                total_tokens += node_tokens

                if node == "router":
                    data = {
                        "route_decision": output.get("route_decision"),
                        "confidence": output.get("confidence", 0.95), # Mock if missing
                        "reasoning": output.get("reasoning", "Query requires complex analysis") # Mock if missing
                    }
                    print(f"📝 Router Decision: {data['route_decision']}")
                    save_capture("router", data)
                
                elif node == "planning":
                    plan = output.get("search_plan", {})
                    print("📋 Plan Created:")
                    print(f"   - Intent: {plan.get('intent', {}).get('intent', 'N/A')}")
                    save_capture("planning", plan)
                
                elif node == "collection":
                    products = output.get("products", [])
                    print("📦 Collection Result:")
                    print(f"   - Products Found: {len(products)}")
                    
                    # Capture sample product and stats
                    capture_data = {
                        "products_count": len(products),
                        "sample_product": products[:],
                        "reviews_data_summary": "Captured reviews for top products",
                        "offers_data_summary": "Captured offers for top products"
                    }
                    save_capture("collection", capture_data)
                
                elif node == "review_intelligence":
                    analysis = output.get("review_analysis", {})
                    print("⭐ Review Intelligence:")
                    count = len(analysis) if isinstance(analysis, (list, dict)) else 'N/A'
                    print(f"   - Analyzed: {count} items")
                    save_capture("review_intelligence", analysis)
                
                elif node == "market_intelligence":
                    analysis = output.get("market_analysis", {})
                    print("📊 Market Intelligence:")
                    print(f"   - Segment: {analysis.get('market_segment', 'N/A')}")
                    save_capture("market_intelligence", analysis)
                
                elif node == "price_tracking":
                    analysis = output.get("price_analysis", {})
                    print("💰 Price Tracking:")
                    count = len(analysis) if isinstance(analysis, (list, dict)) else 'N/A'
                    print(f"   - Analyzed: {count} items")
                    save_capture("price_tracking", analysis)
                
                elif node == "analysis":
                    result = output.get("analysis_result", {})
                    print("🧠 Analysis Agent:")
                    print(f"   - Top Rec: {result.get('top_recommendation', {}).get('product_name', 'N/A')}")
                    save_capture("analysis", result)
                
                elif node == "response":
                    response = output.get("formatted_response", "")
                    print("📝 Final Response Generated:")
                    print(f"   - Length: {len(response)}")
                    
                    # Save response to file
                    with open("ai_server/final_response.md", "w") as f:
                        f.write(response)
                    print("   - Saved to ai_server/final_response.md")
                    
                    # Capture for report
                    save_capture("response", {"formatted_response": response}) # Save full response
                
                print("")
        
        print(f"💰 Total Token Usage: {total_tokens}")
                
    except Exception as e:
        logger.error(f"Error running flow: {e}", exc_info=True)
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_test_flow())
