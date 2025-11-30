# API Specification for Omni-Agent Architecture V2

This document outlines the API endpoints required to support the Omni-Agent Architecture V2, including Streaming, Human-in-the-Loop (HITL), and Feedback.

## Overview

The backend provides a REST API with support for Server-Sent Events (SSE) for real-time streaming.

- **Base URL:** `/api`
- **Content-Type:** `application/json`

## 1. Shopping & Search

### 1.1 Standard Search (Synchronous)
**POST** `/shopping`

Initiates a search or conversation turn.

**Request:**
```json
{
  "query": "I need a gaming laptop under $1500",
  "session_id": "optional-uuid",
  "user_preferences": {
    "user_id": "user-123"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "user_query": "...",
  "matched_products": [...],
  "recommendation": {
    "recommended_product": {...},
    "value_score": 0.95,
    "reasoning": "...",
    "explanation": "..."
  },
  "total_results": 15
}
```

### 1.2 Streaming Search (SSE)
**POST** `/shopping/stream`

Initiates a search with real-time updates. Essential for V2 to show agent thoughts and intermediate steps.

**Request:** Same as `/shopping`

**Events:**

1.  **`start`**: Session started.
    ```json
    {"type": "start", "session_id": "uuid"}
    ```

2.  **`progress`**: High-level status update (Node change).
    ```json
    {
      "type": "progress",
      "step": 1,
      "node": "planning", // e.g., "router", "planning", "collection", "advisory"
      "message": "Planning search strategy..."
    }
    ```

3.  **`chunk`**: LLM token stream (for the final response).
    ```json
    {"type": "chunk", "content": "The best option is..."}
    ```

4.  **[interrupt](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87)** (NEW): HITL trigger. The agent needs user input to proceed.
    ```json
    {
      "type": "interrupt",
      "node": "clarification",
      "message": "Do you prefer 15-inch or 17-inch screens?",
      "thread_id": "uuid" // Required to resume
    }
    ```

5.  **`complete`**: Final result (same structure as synchronous response).
    ```json
    {"type": "complete", "result": {...}}
    ```

6.  **`error`**: Something went wrong.
    ```json
    {"type": "error", "message": "..."}
    ```

## 2. Human-in-the-Loop (HITL)

### 2.1 Resume Execution (NEW)
**POST** `/shopping/resume`

Resumes a paused graph execution after an interrupt.

**Request:**
```json
{
  "session_id": "uuid",
  "thread_id": "uuid", // From the interrupt event
  "user_input": "15-inch please"
}
```

**Response:** (Or Stream)
Returns the final result or continues streaming.

## 3. Feedback Loop

### 3.1 Submit Feedback
**POST** `/shopping` (Standard Endpoint)

Feedback is handled as a natural language turn. The `RouterAgent` classifies it as [feedback](file:///home/thanhnx/e-com/ai_server/agents/feedback_agent.py#15-140).

**Request:**
```json
{
  "query": "That's too expensive",
  "session_id": "uuid"
}
```

**Frontend Behavior:**
- If the user clicks "Thumbs Down", prompt for a reason (e.g., "Price", "Brand", "Features") and send it as a query: "I don't like this because [reason]".
- If the user types a critique, send it as a normal query.

## 4. Session Management

### 4.1 Get Session Details
**GET** `/sessions/{session_id}`

Returns conversation history and learned preferences.

**Response:**
```json
{
  "session_id": "uuid",
  "conversation_history": [
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "ai",
      "content": "...",
      "recommendation": "..."
    }
  ],
  "user_preferences": {
    "liked_brands": ["Sony"],
    "max_budget": 1500
  }
}
```

## Implementation Checklist for Frontend

1.  **Streaming Client:** Implement an SSE client to handle `progress`, `chunk`, and [interrupt](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87) events.
2.  **State Management:** Handle different UI states based on [node](file:///home/thanhnx/e-com/ai_server/agents/router_agent.py#97-229) (e.g., "Searching" vs "Thinking" vs "Asking for Clarification").
3.  **Interrupt UI:** Display the interrupt message and provide an input field (or buttons) for the user to reply. Call `/shopping/resume` with the input.
4.  **Feedback UI:** Allow users to reply to recommendations.
