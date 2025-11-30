# Walkthrough - Phase 1: The Loop (Reflector)

## Overview
We have successfully transformed the linear "Shopping Graph" into a **Cyclic System** capable of self-correction. If the initial search yields poor results (0 items or few matches), the system now automatically retries with a broader strategy.

## Changes Implemented

### 1. Collection Agent ([collection_agent.py](file:///home/thanhnx/e-com/ai_server/agents/collection_agent.py))
- **Status Tracking:** Added logic to calculate `search_status` ("success", "partial", "fail") based on the number of products found.
- **State Update:** Now populates `state["search_status"]`.

### 2. Shopping Graph ([shopping_graph.py](file:///home/thanhnx/e-com/ai_server/graphs/shopping_graph.py))
- **Conditional Routing:** Replaced the direct edge from [Collection](file:///home/thanhnx/e-com/ai_server/schemas/agent_state.py#23-29) to `Intelligence` with a conditional edge [check_search_quality](file:///home/thanhnx/e-com/ai_server/graphs/shopping_graph.py#118-129).
- **Logic:**
    - If `search_status` is "fail" or "partial" AND `retry_count < 3` -> Route back to `Planning`.
    - Otherwise -> Proceed to `Intelligence` agents.

### 3. Planning Agent ([planning_agent.py](file:///home/thanhnx/e-com/ai_server/agents/planning_agent.py))
- **Retry Handling:** Added logic to check for `retry_count`.
- **Strategy Adjustment:** If it's a retry, the agent appends [(IGNORE PREVIOUS CONSTRAINTS. SEARCH BROADLY...)](file:///home/thanhnx/e-com/ai_server/test_product_memory.py#19-24) to the query to force the LLM to generate a more permissive search plan.

## Verification
We verified the logic with a unit test script [ai_server/test_reflection_loop.py](file:///home/thanhnx/e-com/ai_server/test_reflection_loop.py).

### Test Results
```
Ran 3 tests in 0.194s

OK
```
- [test_collection_agent_status](file:///home/thanhnx/e-com/ai_server/test_reflection_loop.py#17-44): Verified status calculation.
- [test_check_search_quality](file:///home/thanhnx/e-com/ai_server/test_reflection_loop.py#45-54): Verified graph routing logic.
- [test_planning_agent_retry](file:///home/thanhnx/e-com/ai_server/test_reflection_loop.py#55-75): Verified query broadening and retry counting.

## Next Steps
Proceed to **Phase 3: The Interrupt (HITL)**, where we will implement the ability to pause and resume conversations for clarification.

# Walkthrough - Phase 2: The Memory (Product Store)

## Overview
We have implemented a persistent **Product Database (SQLite)**. The system now "learns" from every search.

## Changes Implemented

### 1. Product Store ([product_store.py](file:///home/thanhnx/e-com/ai_server/memory/storage/product_store.py))
- **Database:** Created [data/products.db](file:///home/thanhnx/e-com/data/products.db) with a [products](file:///home/thanhnx/e-com/ai_server/memory/storage/product_store.py#117-151) table.
- **Functionality:** Supports [save_product](file:///home/thanhnx/e-com/ai_server/memory/storage/product_store.py#57-92) (upsert) and [search_products](file:///home/thanhnx/e-com/ai_server/memory/storage/product_store.py#117-151) (LIKE query).

### 2. Collection Agent ([collection_agent.py](file:///home/thanhnx/e-com/ai_server/agents/collection_agent.py))
- **Write Path:** Every time the agent finds products on SerpAPI, it immediately saves them to the local database.

### 3. Planning Agent ([planning_agent.py](file:///home/thanhnx/e-com/ai_server/agents/planning_agent.py))
- **Read Path:** Before generating a new search plan, the agent checks the local database.
- **Optimization:** If enough relevant products are found locally (>= 3), it **skips the web search entirely**, saving time and API costs.

## Verification
We verified the logic with [ai_server/test_product_memory.py](file:///home/thanhnx/e-com/ai_server/test_product_memory.py).

### Test Results
```
Ran 3 tests in 0.023s

OK
```
- [test_product_store_crud](file:///home/thanhnx/e-com/ai_server/test_product_memory.py#29-50): Verified DB operations.
- [test_collection_saves_to_store](file:///home/thanhnx/e-com/ai_server/test_product_memory.py#51-72): Verified Collection Agent writes to DB.
- [test_planning_agent_uses_memory](file:///home/thanhnx/e-com/ai_server/test_product_memory.py#73-92): Verified Planning Agent reads from DB and skips search.

# Walkthrough - Phase 3: The Interrupt (HITL)

## Overview
We have refactored the **Clarification Flow** to use LangGraph's [interrupt](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87) mechanism. The system can now pause for user input and resume without losing context.

## Changes Implemented

### 1. Shopping Graph ([shopping_graph.py](file:///home/thanhnx/e-com/ai_server/graphs/shopping_graph.py))
- **Loop Back:** Changed the [clarification](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87) edge to point back to [router](file:///home/thanhnx/e-com/ai_server/agents/router_agent.py#97-200) instead of `END`.
- **Checkpointer:** Enabled `MemorySaver` support for state persistence during interrupts.

### 2. Router Agent ([router_agent.py](file:///home/thanhnx/e-com/ai_server/agents/router_agent.py))
- **Interrupt:** Used [interrupt(message)](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87) in [request_clarification_handler](file:///home/thanhnx/e-com/ai_server/agents/router_agent.py#230-277).
- **Resume Logic:** Captures the user's answer from the interrupt and appends it to `user_query`.

## Verification
We verified the logic with [ai_server/test_hitl.py](file:///home/thanhnx/e-com/ai_server/test_hitl.py).

### Test Results
```
Ran 1 test in 25.695s

OK
Final user query: headphones (User Clarification: Sony under $100)
```
- [test_clarification_interrupt](file:///home/thanhnx/e-com/ai_server/test_hitl.py#18-87): Verified that the graph pauses at clarification, accepts a resume value, updates the query, and completes the workflow.

## Conclusion
All 3 phases of the Architecture Improvement Proposal have been successfully implemented and verified.
1.  **The Loop:** Self-correction for failed searches.
2.  **The Memory:** Persistent product database.
3.  **The Interrupt:** Pause/Resume for clarification.
