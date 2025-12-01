import requests
import json
import time

BASE_URL = "http://localhost:8000/api/shopping"

def test_clarification():
    print("\n=== Testing Clarification Flow ===")
    
    # 1. Send vague query
    query = "headphones"
    print(f"\n1. Sending vague query: '{query}'")
    
    response = requests.post(f"{BASE_URL}", json={
        "query": query,
        "session_id": "test_clarification_session"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response Status: {response.status_code}")
        
        # Check if we got clarification message
        rec = data.get("recommendation", {})
        explanation = rec.get("explanation", "")
        title = rec.get("recommended_product", {}).get("title", "")
        
        print(f"Title: {title}")
        print(f"Explanation: {explanation[:100]}...")
        
        if "Clarification Needed" in title or "thêm thông tin" in explanation:
            print("SUCCESS: Clarification triggered and message received.")
        else:
            print("FAILURE: Did not receive clarification message.")
            print(f"Full response: {json.dumps(data, indent=2)}")
            
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for server...")
    time.sleep(5)
    try:
        test_clarification()
    except Exception as e:
        print(f"Test failed: {e}")
