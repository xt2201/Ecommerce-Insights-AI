# Architecture V2: Real-World Test Plan

This document outlines real-world use cases to verify the **Omni-Agent Architecture**, ensuring all new paths, safety nets, and feedback loops function as designed.

It covers 4 main areas:

- Router & Intents: Verifying Chitchat, FAQ, Advisory, and Search paths.
- HITL Safety Nets: Testing Ambiguity, Execution Failures, and Analysis Uncertainty.
- Feedback Loop: Verifying price and brand critiques.
- Memory: Testing context retention and preference recall.


## 1. Router & Intent Classification

### Case 1.1: Chitchat & Persona
*   **Input:** "Hello, who are you?"
*   **Expected:** `ChitchatAgent` responds. Friendly greeting, identifies as a shopping assistant.
*   **Input:** "Tell me a joke."
*   **Expected:** `ChitchatAgent` responds.

### Case 1.2: FAQ & Policy
*   **Input:** "What is your return policy?"
*   **Expected:** `FAQAgent` responds using knowledge base (mocked).
*   **Input:** "How long does shipping take?"
*   **Expected:** `FAQAgent` responds.

### Case 1.3: Advisory (Consultation)
*   **Input:** "I want to buy a gaming laptop but I don't know what specs I need."
*   **Expected:** `AdvisoryAgent` responds. Asks clarifying questions (GPU, budget, games played) instead of searching immediately.
*   **Follow-up:** "I play Cyberpunk 2077 and have $1500."
*   **Expected:** `AdvisoryAgent` suggests specs (RTX 4060/4070) and asks if user wants to search now.

### Case 1.4: Direct Search
*   **Input:** "iPhone 15 Pro Max 256GB natural titanium"
*   **Expected:** `Router` -> `QuickSearch` -> [Collection](file:///home/thanhnx/e-com/ai_server/schemas/agent_state.py#23-29). Fast path, direct results.

### Case 1.5: Complex Planning
*   **Input:** "Best running shoes for flat feet under $100 that look good with jeans"
*   **Expected:** `Router` -> `Planning`. Agent breaks down requirements (arch support, style, price) and executes a broad search.

## 2. Human-in-the-Loop (HITL) Safety Nets

### Case 2.1: Low Confidence Router (Ambiguity)
*   **Input:** "Apple" (Ambiguous: Fruit? Tech company? Brand?)
*   **Expected:** `Router` interrupts. "I'm not sure if you mean the fruit or the tech brand. Could you clarify?"
*   **User Action:** "The phone brand."
*   **Expected:** Resume -> `Planning` -> Search for Apple products.

### Case 2.2: Execution Failure (Strategy Adjustment)
*   **Input:** "fsdkjfhsjkdfhsdjkf product" (Gibberish or impossible query)
*   **Expected:**
    1.  [Collection](file:///home/thanhnx/e-com/ai_server/schemas/agent_state.py#23-29) finds 0 items.
    2.  `Planning` retries (broadens query).
    3.  [Collection](file:///home/thanhnx/e-com/ai_server/schemas/agent_state.py#23-29) finds 0 items again.
    4.  **Interrupt:** `StrategyAgent` asks: "I'm having trouble finding this. Could you check the spelling or suggest a different keyword?"
*   **User Action:** "Oops, I meant 'fidget spinner'."
*   **Expected:** Resume -> `Planning` -> Search for "fidget spinner".

### Case 2.3: Analysis Uncertainty (Verification)
*   **Input:** "Best laptop for coding under $200" (Unrealistic constraint)
*   **Expected:**
    1.  Search finds very few or poor quality options (Chromebooks, refurbished).
    2.  [Analysis](file:///home/thanhnx/e-com/ai_server/agents/analysis_agent.py#29-512) confidence is low (< 0.5).
    3.  **Interrupt:** [AnalysisAgent](file:///home/thanhnx/e-com/ai_server/agents/analysis_agent.py#29-512) asks: "I found some options, but they might not be great for coding due to the low budget. The top pick is [X]. Do you want to proceed or adjust the budget?"
*   **User Action:** "Show me what you found anyway."
*   **Expected:** Resume -> `Response` generates report with caveats.

## 3. Feedback Loop & Memory

### Case 3.1: Price Feedback (Critique)
*   **Context:** User searches for "Sony headphones" -> System shows $300 options.
*   **Input:** "That's way too expensive. I only have $100."
*   **Expected:**
    1.  `Router` classifies as [feedback](file:///home/thanhnx/e-com/ai_server/agents/feedback_agent.py#15-140).
    2.  `FeedbackAgent` extracts `max_price = 100`.
    3.  `Planning` executes new search for "Sony headphones under $100".
    4.  **Memory:** [UserPreferences](file:///home/thanhnx/e-com/ai_server/schemas/memory_models.py#86-182) updated (price sensitivity).

### Case 3.2: Brand Feedback (Negative)
*   **Context:** System recommends "Bose" headphones.
*   **Input:** "I don't like Bose. They are uncomfortable."
*   **Expected:**
    1.  `FeedbackAgent` extracts `disliked_brands = ["Bose"]`.
    2.  `Planning` executes new search excluding Bose.
    3.  **Memory:** [UserPreferences](file:///home/thanhnx/e-com/ai_server/schemas/memory_models.py#86-182) updated (disliked brand).

### Case 3.3: Follow-up Context
*   **Context:** User looks at "Sony WH-1000XM5".
*   **Input:** "How is the battery life?"
*   **Expected:**
    1.  `Router` classifies as `direct_search` or [planning](file:///home/thanhnx/e-com/ai_server/test_reflection_loop.py#55-75) (depending on implementation) OR [ContextManager](file:///home/thanhnx/e-com/ai_server/memory/context_manager.py#14-80) resolves "battery life" -> "Sony WH-1000XM5 battery life".
    2.  System answers specific question about the product in context.

## 4. Long-Term Memory (Session)

### Case 4.1: Recall Preferences
*   **Session 1:** User says "I hate the color red."
*   **Session 2 (Later):** User searches for "T-shirts".
*   **Expected:** `Planning` or [Analysis](file:///home/thanhnx/e-com/ai_server/agents/analysis_agent.py#29-512) filters out or downranks red t-shirts based on stored preferences.

### Case 4.2: Context Compression (Long Chat)
*   **Action:** Have a 20-turn conversation.
*   **Input (Turn 21):** "What was the first phone we looked at?"
*   **Expected:** System retrieves the first product from [VectorMemory](file:///home/thanhnx/e-com/ai_server/memory/vector_memory.py#16-119) or `Summary` and answers correctly, despite it being out of the immediate context window.
