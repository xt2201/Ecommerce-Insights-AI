#!/usr/bin/env python3
"""Simple test to verify session persistence with debug logging."""

import requests
import json

BASE_URL = "http://localhost:8000/api/shopping"
SESSION_URL = "http://localhost:8000/api/sessions"

# Create session
print("Creating session...")
session_resp = requests.post(SESSION_URL, json={"user_id": "test_user"})
session_id = session_resp.json()["session_id"]
print(f"Session ID: {session_id}\n")

# Turn 1: Specific product
print("=" * 60)
print("TURN 1: Sony WH-1000XM5")
print("=" * 60)
resp1 = requests.post(f"{BASE_URL}/stream", json={"query": "Sony WH-1000XM5", "session_id": session_id}, stream=True)
for line in resp1.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith("data: "):
            try:
                data = json.loads(decoded[6:])
                if data.get("type") == "complete":
                    print("✅ Turn 1 complete\n")
                    break
            except:
                pass

# Turn 2: Follow-up
print("=" * 60)
print("TURN 2: cheaper options (FOLLOW-UP)")
print("=" * 60)
resp2 = requests.post(f"{BASE_URL}/stream", json={"query": "cheaper options", "session_id": session_id}, stream=True)
for line in resp2.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith("data: "):
            try:
                data = json.loads(decoded[6:])
                if data.get("type") == "interrupt":
                    print(f"⚠️ INTERRUPT: {data.get('message')}\n")
                    break
                elif data.get("type") == "complete":
                    print("✅ Turn 2 complete (no interrupt!)\n")
                    break
            except:
                pass

print("\nCheck backend logs for:")
print("  docker logs ecom-backend --tail 50 | grep -E '(previous_queries|IsFollowup)'")
