import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_server.core.config import load_config
from ai_server.agents.planning_agent import plan_search
from ai_server.schemas.agent_state import AgentState

# Load environment variables
load_dotenv()
load_config()

def test_planning_optimization():
    print("🚀 Testing Optimized Planning Agent...")
    
    # Test queries
    queries = [
        "wireless noise cancelling headphones under $200",
        "best gaming laptop for valorant",
        "cheap running shoes nike"
    ]
    
    for query in queries:
        print(f"\n📋 Query: {query}")
        
        # Initialize state
        state = AgentState(
            user_query=query,
            conversation_history=[],
            user_preferences=None,  # Will be initialized by agent if needed
            debug_notes=[]
        )
        
        try:
            # Run planning agent
            result_state = plan_search(state)
            
            # Check results
            plan = result_state.get("search_plan")
            notes = result_state.get("debug_notes", [])
            
            if plan:
                print("✅ Plan generated successfully!")
                print(f"   - Keywords: {plan.get('keywords')}")
                print(f"   - Max Price: {plan.get('max_price')}")
                print(f"   - Engines: {plan.get('engines')}")
                print(f"   - Requirements: {json.dumps(plan.get('requirements', {}), indent=2)}")
                
                # Check if "Generating comprehensive plan" is in notes
                if any("Generating comprehensive plan" in note for note in notes):
                    print("✅ Confirmed usage of optimized tool")
                else:
                    print("❌ Warning: Optimized tool usage not found in logs")
            else:
                print("❌ Failed to generate plan")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_planning_optimization()
