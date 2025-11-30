#!/usr/bin/env python3
"""Test follow-up queries and memory handling."""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/shopping"
SESSION_URL = "http://localhost:8000/api/sessions"

def create_session():
    """Create a new session."""
    response = requests.post(SESSION_URL, json={"user_id": "test_user"})
    return response.json()["session_id"]

def send_query(session_id, query, print_events=False):
    """Send a query and return result."""
    print(f"\n{'='*60}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")
    
    payload = {"query": query, "session_id": session_id}
    
    events = []
    with requests.post(f"{BASE_URL}/stream", json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        events.append(data)
                        
                        if print_events:
                            if data["type"] == "node_output":
                                print(f"  → Node: {data['node']}")
                            elif data["type"] == "interrupt":
                                print(f"  ⚠ INTERRUPT: {data.get('message', 'N/A')}")
                        
                        if data["type"] == "complete":
                            return data.get("result"), events
                    except json.JSONDecodeError:
                        pass
    return None, events

def check_route(events, expected_route):
    """Check if a specific route/node was hit."""
    nodes = [e.get("node") for e in events if e.get("type") == "node_output"]
    return expected_route in nodes

def test_scenario(name, queries, session_id=None):
    """Test a multi-turn conversation scenario."""
    print(f"\n{'#'*60}")
    print(f"# TEST SCENARIO: {name}")
    print(f"{'#'*60}")
    
    if session_id is None:
        session_id = create_session()
        print(f"Created new session: {session_id}")
    
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\nTurn {i}:")
        result, events = send_query(session_id, query, print_events=True)
        
        # Check for interrupts (clarification requests)
        has_interrupt = any(e.get("type") == "interrupt" for e in events)
        hit_planning = check_route(events, "planning")
        hit_clarification = check_route(events, "clarification")
        
        status = {
            "query": query,
            "has_interrupt": has_interrupt,
            "hit_planning": hit_planning,
            "hit_clarification": hit_clarification,
            "result": result is not None
        }
        results.append(status)
        
        print(f"\n  Status: Interrupt={has_interrupt}, Planning={hit_planning}, Clarification={hit_clarification}")
        
        # Small delay between turns
        time.sleep(0.5)
    
    return results

def main():
    print("="*60)
    print("FOLLOW-UP QUERY & MEMORY TEST SUITE")
    print("="*60)
    
    # Scenario 1: Follow-up with refinement
    print("\n\n")
    results1 = test_scenario(
        "Follow-up Refinement",
        [
            "Sony WH-1000XM5",  # Specific product
            "cheaper options",  # Follow-up: should use context
            "with better battery life"  # Another follow-up
        ]
    )
    
    # Scenario 2: Follow-up after initial search
    print("\n\n")
    results2 = test_scenario(
        "Price-based Follow-up",
        [
            "wireless gaming mouse",  # General search
            "under $50",  # Follow-up with price constraint
            "from Logitech"  # Follow-up with brand constraint
        ]
    )
    
    # Scenario 3: Comparative follow-up
    print("\n\n")
    results3 = test_scenario(
        "Comparative Follow-up",
        [
            "iPhone 15",  # Specific product
            "what about Samsung?",  # Follow-up comparison
            "cheaper than both"  # Follow-up with comparison
        ]
    )
    
    # Scenario 4: Follow-up after clarification
    print("\n\n")
    results4 = test_scenario(
        "Clarification then Follow-up",
        [
            "tai nghe",  # Should trigger clarification
            # NOTE: This will interrupt, so we can't continue automatically
        ]
    )
    
    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_scenarios = [
        ("Follow-up Refinement", results1),
        ("Price-based Follow-up", results2),
        ("Comparative Follow-up", results3),
        ("Clarification then Follow-up", results4)
    ]
    
    for scenario_name, results in all_scenarios:
        print(f"\n{scenario_name}:")
        for i, r in enumerate(results, 1):
            symbol = "✅" if not r["has_interrupt"] else "⚠️"
            print(f"  Turn {i}: {symbol} '{r['query'][:40]}...' | Planning={r['hit_planning']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()
