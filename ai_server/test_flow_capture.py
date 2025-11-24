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
        "chat_history": [],
        "trace_id": f"test_run_{int(time.time())}"
    }
    
    try:
        # Run graph
        async for event in graph.astream(initial_state):
            for node, output in event.items():
                print(f"📍 Node Completed: {node.upper()}")
                
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
                    print(f"   - Intent: {plan.get('intent', {}).get('primary_intent', 'N/A')}")
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
                    print(f"   - Analyzed: {len(analysis) if isinstance(analysis, list) else 'N/A'} items")
                    save_capture("review_intelligence", analysis)
                
                elif node == "market_intelligence":
                    analysis = output.get("market_analysis", {})
                    print("📊 Market Intelligence:")
                    print(f"   - Segment: {analysis.get('market_segment', 'N/A')}")
                    save_capture("market_intelligence", analysis)
                
                elif node == "price_tracking":
                    analysis = output.get("price_analysis", {})
                    print("💰 Price Tracking:")
                    print(f"   - Analyzed: {len(analysis) if isinstance(analysis, list) else 'N/A'} items")
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
                
    except Exception as e:
        logger.error(f"Error running flow: {e}", exc_info=True)
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_test_flow())
