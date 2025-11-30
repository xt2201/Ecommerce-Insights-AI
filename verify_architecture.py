import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000/api/shopping"
SESSION_URL = "http://localhost:8000/api/sessions"

def create_session():
    response = requests.post(SESSION_URL, json={"user_id": "test_user"})
    return response.json()["session_id"]

def send_query(session_id, query):
    print(f"\n--- Sending Query: '{query}' ---")
    payload = {
        "query": query,
        "session_id": session_id
    }
    
    # Use streaming endpoint to see events
    events = []
    try:
        with requests.post(f"{BASE_URL}/stream", json=payload, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            if data["type"] == "node_output":
                                print(f"Node Output: {data['node']}")
                                events.append(data)
                            elif data["type"] == "interrupt":
                                print(f"INTERRUPT: {data['node']} - {data['message']}")
                                events.append(data)
                            elif data["type"] == "complete":
                                print("Request Complete")
                                return data["result"], events
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"Request failed: {e}")
        return None, events
    return None, events

def test_ambiguous_query():
    print("\n=== TEST 1: Ambiguous Query (HITL1) ===")
    session_id = create_session()
    result, events = send_query(session_id, "tai nghe")
    
    # Check if clarification node was hit or interrupt occurred
    clarification_hit = any(e.get("node") == "clarification" for e in events)
    interrupt_hit = any(e.get("type") == "interrupt" for e in events)
    
    if clarification_hit or interrupt_hit:
        print("✅ PASS: System asked for clarification.")
    else:
        print("❌ FAIL: System did not ask for clarification.")

def test_chitchat():
    print("\n=== TEST 2: Chitchat ===")
    session_id = create_session()
    result, events = send_query(session_id, "Hello, how are you?")
    
    chitchat_hit = any(e.get("node") == "chitchat" for e in events)
    if chitchat_hit:
        print("✅ PASS: Chitchat agent triggered.")
    else:
        print("❌ FAIL: Chitchat agent NOT triggered.")

def test_advisory():
    print("\n=== TEST 3: Advisory ===")
    session_id = create_session()
    result, events = send_query(session_id, "What should I look for in a gaming laptop?")
    
    advisory_hit = any(e.get("node") == "advisory" for e in events)
    if advisory_hit:
        print("✅ PASS: Advisory agent triggered.")
    else:
        print("❌ FAIL: Advisory agent NOT triggered.")

def test_followup_memory():
    print("\n=== TEST 4: Follow-up Memory ===")
    session_id = create_session()
    
    # 1. Initial Search
    print("Step 1: Initial Search (Sony Headphones)")
    send_query(session_id, "Sony WH-1000XM5")
    
    # 2. Follow-up
    print("Step 2: Follow-up (Cheaper)")
    result, events = send_query(session_id, "Any cheaper options?")
    
    # Check if planning node received context
    # We can't easily check internal state, but we can check if it performed a search
    # and if the result contains different products.
    # Ideally, we'd check logs, but here we check if it went to planning/collection
    planning_hit = any(e.get("node") == "planning" for e in events)
    
    if planning_hit:
        print("✅ PASS: Follow-up triggered planning (implies context usage).")
    else:
        print("❌ FAIL: Follow-up did not trigger planning.")

def test_faq():
    print("\n=== TEST 5: FAQ ===")
    session_id = create_session()
    result, events = send_query(session_id, "What is your return policy?")
    
    faq_hit = any(e.get("node") == "faq" for e in events)
    if faq_hit:
        print("✅ PASS: FAQ agent triggered.")
    else:
        print("❌ FAIL: FAQ agent NOT triggered.")

if __name__ == "__main__":
    try:
        test_ambiguous_query()
        test_chitchat()
        test_advisory()
        test_faq()
        test_followup_memory()
    except Exception as e:
        print(f"Test failed with error: {e}")
