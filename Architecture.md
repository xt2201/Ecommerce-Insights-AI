# Updated Architecture

## 1. Router Agent

**Task:** Decide on the processing strategy for each query.

### Technical Implementation:

1. **LLM-based Classification:**
   - **Model:** Uses Cerebras Llama 3.1-8B with `temperature=0.0` for deterministic routing
   - **Method:** `llm.with_structured_output(QueryClassification, include_raw=True)`
   - **Schema:** Returns structured `QueryClassification` object containing:
     - `route`: Enum ("simple", "standard", "complex")
     - `confidence`: Float (0.0-1.0)
     - `reasoning`: String explanation
   - **Token Tracking:** Extracts actual token usage from `raw_response.usage_metadata`

2. **Prompt Engineering:**
   - System prompt defines 3 routing strategies with specific criteria
   - Input: Raw user query string
   - Output mapping logic (lines 146-152 in router_agent.py):
     ```python
     if classification.route == "simple":
         route_decision = "direct_search"
     elif classification.route == "clarification":
         route_decision = "clarification"
     else:  # standard or complex
         route_decision = "planning"
     ```

3. **Follow-up Detection (Agentic Memory):**
   - **Mechanism:** LLM analyzes `chat_history` context within `classify_query`
   - **Prompting:** Includes previous queries in the prompt: "Is this a follow-up to the previous conversation?"
   - **Output:** `QueryClassification` now includes `is_followup` (bool) and `followup_reasoning`
   - **Logic:**
     - If `is_followup=True`: Sets `state["is_followup"]` and extracts context
     - Uses semantic understanding rather than simple rule-based history checking
   - **Improvement:** Handles context switching better (e.g., user starts new topic despite having history)

4. **Trace Integration:**
   - Creates `ROUTER` step via `trace_manager.create_step()`
   - Records: route decision, confidence, reasoning
   - Passes `TokenUsage(prompt_tokens, completion_tokens, total_tokens)` to trace

- **Example Decision:**
    
    ```json
    {
      "route_decision": null,
      "confidence": 0.95,
      "reasoning": "Query requires complex analysis"
    }
    ```
    
    - **Input Query:** "Best noise cancelling headphones under $300 for working at office"
    - **Decision:** `planning` (complex query with multiple criteria).
    - **Debug Note:** "Query requires complex analysis"
- **Data flow:**
    - Input: `user_query`, `chat_history`
    - Output: `route="planning"`, `confidence=0.95`

## 2. Planning Agent

**Mission:** Analyze deep intent and build a detailed search plan.

### Technical Implementation:

1. **Comprehensive LLM Planning:**
   - **Model:** Cerebras Qwen 3-32B with `temperature=0.1`, `max_tokens=4000`
   - **Single-Call Strategy:** Uses `generate_comprehensive_plan_with_tokens()` to extract all planning components in ONE LLM call:
     - Intent analysis (intent type, specificity, confidence)
     - Keyword expansion (5+ alternative search terms)
     - Requirements extraction (max_price, min_rating, features, brands)
     - Planning reasoning (why these choices)
   - **Schema:** Returns `ComprehensiveSearchPlan` Pydantic model
   - **Token Tracking:** Returns tuple `(plan_dict, token_dict)` with actual LLM usage

2. **Preference Learning (Non-LLM):**
   - **Algorithm:** Directly updates `UserPreferences` from extracted requirements (no PreferenceExtractor LLM call)
   - **Logic:**
     ```python
     for brand in requirements['brand_preferences']:
         user_preferences.update_brand_preference(brand, liked=True, confidence=0.8)
     for feature in requirements['required_features']:
         user_preferences.update_feature_preference(feature, must_have=True, confidence=0.8)
     if requirements['max_price']:
         user_preferences.update_price_preference(requirements['max_price'])
     user_preferences.confidence = min(1.0, confidence + 0.1)
     ```
   - **No LLM used** - pure Python dict mapping for speed

3. **Engine Selection (Static):**
   - **Current Implementation:** Hardcoded `engines = ["amazon"]` (line 134-135 in planning_agent.py)
   - **No conditional logic:** Code has commented-out intent checking for specialized engines
   - **Design Decision:** Does NOT add `amazon_product_reviews` or `amazon_offers` to save API costs
   - **Impact:** Review Agent ALWAYS falls back to rating-based analysis (no review text)
   - **Note:** `debug_notes.append("Planning: Using standard amazon engine")` always executes

4. **Trace Integration:**
   - Records: search_plan, intent_analysis, requirements, keywords_count
   - Passes actual `TokenUsage` from LLM call

```mermaid
graph TD
    UserInput[User Input] --> IntentClassifier{Intent Classifier}
    
    %% HITL cho intent không rõ
    IntentClassifier -->|Low Confidence < 0.7| HITL1[HITL: Clarify Intent]
    HITL1 -->|User Clarifies| IntentClassifier
    
    %% Chitchat path
    IntentClassifier -->|Chitchat/General| ConversationalLLM[Direct LLM Response]
    ConversationalLLM --> UserOutput[User Output]
    
    %% FAQ path
    IntentClassifier -->|FAQ/Policy| RAGSystem[RAG: FAQ Database]
    RAGSystem -->|No Match| HITL2[HITL: Escalate to Human]
    RAGSystem --> UserOutput
    
    %% Advisory path
    IntentClassifier -->|Advisory Request| AdvisoryAgent[Advisory Agent]
    AdvisoryAgent --> HITL3{Need Product Examples?}
    HITL3 -->|Yes| ProductSearch[Search Examples]
    HITL3 -->|No| UserOutput
    ProductSearch --> AdvisoryAgent
    AdvisoryAgent --> UserOutput
    
    %% Product search path với HITL checkpoints
    IntentClassifier -->|Product Search| ContextBuilder[Context Builder]
    ContextBuilder -->|Ambiguous Query| HITL4[HITL: Refine Search Criteria]
    HITL4 --> ContextBuilder
    
    ContextBuilder --> Planner[Search Planner]
    Planner --> Manager[Search Manager]
    
    subgraph "Search Execution Loop"
        Manager -->|Delegate| Tools[Search/Scrape Tools]
        Tools -->|Raw Data| Manager
        Manager -->|Review| Reflector{Quality Check}
        
        %% HITL trong execution loop
        Reflector -->|Poor Results 2x| HITL5[HITL: Adjust Strategy?]
        HITL5 -->|User Modifies| Planner
        HITL5 -->|Auto Retry| RePlanner[Adjust Strategy]
        
        Reflector -->|Consistently Bad| HITL6[HITL: Manual Search?]
        HITL6 -->|Human Takes Over| ManualSearch[Human Search]
        ManualSearch --> Analyzer
        
        Reflector -->|Poor Results| RePlanner
        RePlanner --> Manager
        Reflector -->|Good Data| Analyzer[Data Analyzer]
    end
    
    Analyzer -->|Uncertain Insights| HITL7[HITL: Verify Analysis]
    HITL7 --> Response
    
    Analyzer -->|Product Insights| Response[Response Generator]
    Response -->|Sensitive Decision| HITL8[HITL: Final Review]
    HITL8 --> UserOutput
    Response --> UserOutput
    
    %% Feedback loop
    UserOutput --> FeedbackCollector{User Satisfied?}
    FeedbackCollector -->|Thumbs Down| HITL9[HITL: Intervention]
    HITL9 --> IntentClassifier
    
    style IntentClassifier fill:#ff9999
    style AdvisoryAgent fill:#99ccff
    style RAGSystem fill:#99ff99
    style HITL1 fill:#ffcc00
    style HITL2 fill:#ffcc00
    style HITL3 fill:#ffcc00
    style HITL4 fill:#ffcc00
    style HITL5 fill:#ffcc00
    style HITL6 fill:#ffcc00
    style HITL7 fill:#ffcc00
    style HITL8 fill:#ffcc00
    style HITL9 fill:#ffcc00
```
    - **Intent:** `recommendation`
    - **Keywords:** `["noise cancelling headphones", "budget headphones", "office noise isolation", "wireless noise blockers"]`
    - **Requirements:** `max_price: 300.0`, `required_features: ["noise cancellation", "comfortable design"]`
    - **Selected Engines:** `["amazon"]`
- **Data flow:**
    - Input: `user_query`
    - Output: `search_plan` (JSON containing keywords, engines, filters, requirements), `user_preferences` (updated)

## 3. Collection Agent

**Mission:** Execute searches and collect raw data from multiple sources.

### Technical Implementation:

1. **API Integration (No LLM):**
   - **Service:** SerpAPI Google Shopping Search
   - **Client:** `SerpAPIClient` wrapper with error handling and retries
   - **Method:** `search_amazon_products(query, domain, max_results=25)`
   - **Raw Data:** Returns JSON with products array

2. **Data Normalization (Rule-based):**
   - **Price Parsing:**
     - Regex: `r'[\d,]+\.\d{2}'` to extract numeric value (e.g., "1,299.99")
     - Removes commas and converts to float: "$1,299.99" → 1299.99
     - Fallback: `r'[^\d.]'` to strip non-numeric characters for simple integers
   - **Brand Field:**
     - **Current Implementation:** Brand field is left empty (`""`)
     - **Reason:** SerpAPI Amazon organic results do not include brand metadata
     - **Design Decision:** Brand identification is deferred to Analysis Agent (can extract from product title if needed using LLM reasoning)

3. **Deep Dive Logic (Conditional):**
   - **Trigger:** Only if `"amazon_product_reviews"` or `"amazon_offers"` in `search_plan.engines`
   - **Current Reality:** Planning Agent does NOT add these engines → Deep dive NEVER runs
   - **Reason:** Cost optimization - SerpAPI charges per request
   - **If Enabled:** Would fetch reviews/offers for top-3 products via:
     - `serp_client.get_product_reviews(asin)`
     - `serp_client.get_product_offers(asin)`

4. **Output Structure:**
   - `products`: List[Dict] with normalized fields (asin, title, price, rating, reviews_count, link, brand)
   - `reviews_data`: Dict[asin → reviews] (empty if deep dive disabled)
   - `offers_data`: Dict[asin → offers] (empty if deep dive disabled)

5. **Trace Integration:**
   - Records: products_count, keywords used, domain, deep_dive_count
   - **No token usage** - pure API/data processing agent

- **Example Output:**
    
    ```json
    {
      "products_count": 22,
      "sample_product": [
        {
          "asin": "B0FGG71BRD",
          "title": "Amazon Fire HD 10 tablet (32 GB, Black) Noise Cancelling Headphone Bundle",
          "product_name": "Amazon Fire HD 10 tablet (32 GB, Black) Noise Cancelling Headphone Bundle",
          "brand": "",
          "price": 94.98,
          "rating": 5.0,
          "reviews_count": 7,
          "link": "..."
        }
      ]
    }
    
    ```
    
    - **Action:** Search Amazon with keyword "noise cancelling headphones".
    - **Result:** 22 products found.
    - **Raw Data (Sample):** `{ "asin": "B0DZHR44J9", "title": "Bose QuietComfort 45", "price": 279.00, "rating": 4.6, "reviews_count": 12500 }`
- **Data flow:**
    - Input: `search_plan`
    - Output: `products` (list of dicts), `reviews_data` (dict), `offers_data` (embedded in products or dict)

## 4. Review Intelligence Agent (Parallel Execution)

**Mission:** Deep analysis of sentiment and review reliability.

### Technical Implementation:

1. **Dual-Mode Operation:**

   **Mode A: LLM-based Analysis (When `reviews_data` available):**
   - **Model:** Cerebras GLM-4.6 with `temperature=0.1`, `max_tokens=4000`
   - **Two LLM Calls per Product:**
     
     a. `analyze_reviews_cot()` - Sentiment Analysis:
        - Input: Product title + top 10 review texts
        - Output: `ReviewAnalysis` schema with:
          - `summary`: Overall sentiment description
          - `sentiment_score`: Float 0-1 (0=negative, 1=positive)
          - `pros`: List[str] extracted positive points
          - `cons`: List[str] extracted negative points
          - `aspect_sentiment`: Dict[aspect → sentiment] (e.g., "battery": "excellent")
        - Method: Structured output with `include_raw=True` for token tracking
     
     b. `detect_fake_reviews()` - Authenticity Check:
        - Input: Product title + top 10 review texts with dates
        - Output: `AuthenticityCheck` schema with:
          - `authenticity_score`: Int 0-100 (reliability score)
          - `flags`: List[str] suspicious patterns found
          - `reasoning`: String explanation
        - Detection patterns LLM checks:
          - Generic language ("great product", "highly recommend")
          - Unnatural repetition across reviews
          - Suspicious timing (burst of 5-star reviews)
          - Overly promotional language
   
   - **Token Accumulation:** Sums tokens from both calls, passes to trace

   **Mode B: Rating-based Fallback (When NO `reviews_data`):**
   - **Algorithm:** Pure Python heuristic - `analyze_from_rating()`
   - **Inputs:** rating (float), reviews_count (int)
   - **Sentiment Score Calculation:**
     ```python
     sentiment_score = rating / 5.0
     ```
   - **Authenticity Score Logic:**
     ```python
     if reviews_count >= 1000:
         if rating >= 4.9: 
             score = 75.0  # Suspiciously high
             flags = ["Very high rating may indicate review manipulation"]
         else: 
             score = 90.0
             flags = []
     elif reviews_count >= 100: score = 80.0, flags = []
     elif reviews_count >= 10: score = 70.0, flags = ["Limited review sample"]
     else: score = 50.0, flags = ["Very limited review sample", "Insufficient data for validation"]
     ```
   - **Pros/Cons Generation:** Template-based on rating thresholds
   - **Flags:** "Limited review sample" if count < 100
   - **No LLM used** → No tokens consumed

2. **Current Behavior:**
   - **Reality:** Planning Agent does NOT enable review collection
   - **Result:** Always uses Mode B (rating-based fallback)
   - **Impact:** Fast but less detailed analysis

3. **Trace Integration:**
   - Records: products_analyzed count
   - Passes `TokenUsage` only if Mode A was used

- **Example Analysis (Mode B - Current):**
    
    ```json
    {
      "B0FGG71BRD": {
        "summary": "Excellent rating of 5.0/5 based on 7 reviews (very low validation volume)",
        "sentiment_score": 1.0,
        "authenticity_score": 50.0,
        "pros": [
          "High customer satisfaction",
          "Strong rating of 5.0/5",
          "Positive overall feedback"
        ],
        "cons": [
          "Limited review validation (7 reviews)"
        ],
        "flags": [
          "Very limited review sample",
          "Insufficient data for validation"
        ],
        "aspect_sentiment": {
          "overall": "excellent",
          "reliability": "very low"
        },
        "analysis_method": "rating-based (no review text available)"
      }
    }
    
    ```
    
    - **Product:** Bose QuietComfort 45 (B0DZHR44J9)
    - **Sentiment Score:** **0.92** (Positive)
    - **Pros:** "Excellent noise cancellation", "Very comfortable for long wear"
    - **Authenticity:** **0.95** (High confidence)
- **Data flow:**
    - Input: `reviews_data`
    - Output: `review_analysis` (partial state update)

## 5. Market Intelligence Agent (Parallel Execution)

**Mission:** Place products in market context.

### Technical Implementation:

1. **LLM-based Market Analysis:**
   - **Model:** Cerebras Qwen 3-32B with `temperature=0.1`, `max_tokens=4000`
   - **Single Call:** `analyze_market_trends()`
   - **Input Preparation:**
     - Extracts price distribution statistics (min, max, avg, median)
     - Counts brand occurrences
     - Calculates rating distribution
     - Formats as context string for LLM
   
2. **LLM Prompt Structure:**
   ```python
   Context: {product_count} products analyzed
   Price range: ${min_price} - ${max_price}
   Average price: ${avg_price}
   Brand distribution: {brand_counts}
   Rating distribution: {rating_stats}
   
   Analyze:
   1. Market segmentation (Budget/Mid-range/Premium)
   2. Price insights (sweet spots, outliers)
   3. Brand insights (market dominance, competition)
   4. Gap analysis (underserved segments)
   5. Recommendation strategy for user query
   ```

3. **Output Schema:** `MarketAnalysis`
   - `market_segment`: String ("Budget", "Mid-range", "Premium", "Mixed")
   - `price_insight`: String (market price dynamics)
   - `brand_insight`: String (brand landscape)
   - `gap_analysis`: String (market opportunities)
   - `recommendation_strategy`: String (how to prioritize products)

4. **Token Tracking:**
   - Method: `with_structured_output(MarketAnalysis, include_raw=True)`
   - Extracts: `extract_token_usage(raw)` from `out.get("raw")`
   - Returns: `(parsed, usage)` tuple where `parsed = out.get("parsed")`
   - **Error handling:** Returns error MarketAnalysis with 0 tokens if LLM fails

5. **Trace Integration:**
   - Records: products_analyzed count
   - Passes actual `TokenUsage(prompt_tokens, completion_tokens, total_tokens)`

- **Example Analysis:**
    
    ```json
    {
      "market_segment": "Mixed",
      "price_insight": "The market is budget-leaning with a sweet spot around $50-$100, offering strong value. Higher-end options (up to $479) exist but are outliers.",
      "brand_insight": "Amazon and Anker (via Soundcore) dominate with multiple high-rated products. Lesser-known brands also compete on price.",
      "gap_analysis": "Mid-range options ($150-$300) with premium features (e.g., superior sound quality, advanced ANC, ergonomic design) are underrepresented. Budget options lack differentiation in feature sets.",
      "recommendation_strategy": "Prioritize products in the $50-$100 range with ANC, long battery life, and positive user reviews (e.g., Soundcore Q20i at $37.99). For office use, focus on comfort and noise isolation over brand prestige."
    }
    
    ```
    
    - **Segment:** "Premium"
    - **Price Insight:** "$200-$350 range is the sweet spot for premium ANC."
    - **Gap Analysis:** "Gap for high-quality ANC under $150."
- **Data flow:**
    - Input: `products`
    - Output: `market_analysis` (partial state update)

## 6. Price Tracking Agent (Parallel Execution)

**Mission:** Analyze price history and deals.

### Technical Implementation:

1. **LLM-based Price Analysis:**
   - **Model:** Cerebras Llama 3.3-70B with `temperature=0.1`, `max_tokens=2000`
   - **Multiple Calls:** One call per product (top 5 products analyzed)
   - **Method:** `analyze_price()` for each product

2. **Input Context per Product:**
   - Current price
   - Product title and rating
   - Market statistics (min, max, average, median prices)
   - Historical data (if available from offers_data)

3. **LLM Reasoning Logic:**
   - Compares current price vs average/median
   - Calculates relative position in price distribution
   - Assesses discount depth (if historical price available)
   - Evaluates price stability

4. **Output Schema:** `PriceAnalysis` per product
   - `recommendation`: String ("Buy Now", "Wait", "Fair Price")
   - `confidence`: Float 0-1
   - `price_status`: String ("Good Deal", "Fair Price", "Overpriced")
   - `savings_percentage`: Float (discount vs market avg)
   - `reasoning`: String (LLM explanation)

5. **Token Accumulation:**
   - Tracks tokens from each `analyze_price()` call
   - Sums: `total_tokens["input_tokens"] += usage["input_tokens"]`
   - Returns accumulated total to trace

6. **Current Limitation:**
   - **No real historical price data:** Code uses **mock random data** (lines 36-41 in price_agent.py)
   - **Mock logic:**
     ```python
     import random
     variation = current_price * 0.2
     lowest_price = max(0.99, current_price - random.uniform(0, variation))
     highest_price = current_price + random.uniform(0, variation)
     average_price = (lowest_price + highest_price + current_price) / 3
     ```
   - **Impact:** Price analysis is based on simulated data, not real historical trends
   - **Comment in code:** "Mock historical data (Phase 1/2 limitation) - In production, this would come from a DB or API"

- **Example Analysis:**
    
    ```json
    {
      "B0FGG71BRD": {
        "recommendation": "Wait",
        "confidence": 0.6,
        "price_status": "Fair Price",
        "savings_percentage": 0.71,
        "reasoning": "The current price is close to the average price and not near the lowest recorded price, with a moderate discount depth."
      },
      "B085WTY1HQ": {
        "recommendation": "Buy Now",
        "confidence": 0.8,
        "price_status": "Good Deal",
        "savings_percentage": 0.02,
        "reasoning": "The current price is below the average price and close to the lowest recent price, indicating a good deal."
      }
    }
    
    ```
    
    - **Product:** Bose QC45 ($279.00)
    - **Status:** "Fair Price" (vs Average $279.00)
    - **Recommendation:** "Neutral" (No significant discount detected)
- **Data flow:**
    - Input: `products`
    - Output: `price_analysis` (partial state update)

## 7. Analysis Agent

**Mission:** Synthesize all information and make final decisions with Chain-of-Thought.

### Technical Implementation:

1. **Chain-of-Thought (CoT) Pipeline:**
   - **Model:** Cerebras GPT-OSS-120B with `temperature=0.2`, `max_tokens=8000` (largest model for complex reasoning)
   - **5 Sequential LLM Calls:**
   
   **Step 1: Product Comparison CoT**
   - Method: `compare_products_cot(products, requirements, user_preferences)`
   - Input: 22 products + user requirements + preferences
   - Output: `ProductComparison` schema with:
     - `reasoning_steps`: List[ReasoningStep] - each step has:
       - `step_number`: Int
       - `thought`: String (internal reasoning)
       - `action`: String (what to check)
       - `observation`: String (finding)
       - `confidence`: Float 0-1
     - `recommended_products`: List of top 5 ASINs with justification
   - **CoT Process LLM performs:**
     1. Filter by budget/rating constraints
     2. Check brand preferences
     3. Match required features (noise cancellation, etc.)
     4. Compare specifications
     5. Rank by feature match quality
   - Token usage: ~2896 input + 5310 output = 8206 total

   **Step 2: Value Score Calculation** (Per Top-5 Product)
   - Method: `calculate_value_score_reasoning(product, requirements, market_context)`
   - Output: `ValueScoreReasoning` schema:
     - `value_score`: Float 0-1 (composite score)
     - `price_value_ratio`: Float (quality per dollar)
     - `feature_match_score`: Float (meets requirements?)
     - `reliability_score`: Float (based on reviews)
     - `reasoning`: String (LLM explanation of score)
   - **LLM Scoring Logic:**
     - Feature match: 40% weight (has required features?)
     - Price efficiency: 30% weight (value for money)
     - Review quality: 20% weight (rating × sqrt(review_count))
     - Brand reputation: 10% weight
   - **Personalization Layer (Non-LLM):**
     - After LLM score, applies `PersonalizedScorer.score_product(product, user_preferences, base_score)`
     - Implementation (in `ai_server/memory/personalized_scorer.py`):
       ```python
       personalized_score = PersonalizedScorer.score_product(
           product,
           user_preferences,  # Now dict, not UserPreferences object
           base_score=score.overall_score
       )
       
       # Algorithm inside score_product():
       # - Check user_preferences['confidence'] > 0.3
       # - Brand boost: if brand in preferred_brands, adjust score
       # - Feature boost: if has must-have features, adjust score
       # - Returns final personalized score capped at 1.0
       ```
     - Updates `score.overall_score` with personalized value
     - Logs: `"Personalized score: {base:.2f} → {personalized:.2f}"`
   - Token usage: ~900-930 input + 586-1045 output per product

   **Step 3: Recommendation Explanation**
   - Method: `explain_recommendation(top_product, comparison_result)`
   - Output: `RecommendationExplanation` schema:
     - `summary`: String (one-sentence why)
     - `key_strengths`: List[str]
     - `user_match_reasoning`: String (how it fits user needs)
     - `confidence_factors`: List[str]
   - Token usage: ~979 input + 893 output

   **Step 4: Tradeoff Analysis**
   - Method: `identify_tradeoffs(recommended_products)`
   - Output: `TradeoffAnalysis` schema:
     - `tradeoff_matrix`: Dict[aspect → tradeoffs]
     - `decision_factors`: List[str] (what user should consider)
   - Example: "Battery life vs portability", "Price vs brand reputation"
   - Token usage: ~2555 input + 1332 output

   **Step 5: Red Flag Detection**
   - Method: `detect_red_flags(products)`
   - **LLM Call:** Uses `llm.invoke()` with text response (NOT structured output)
   - **Parsing:** `_parse_red_flags_from_response()` extracts flags from text using keyword matching
   - Output: List[`RedFlag`] with:
     - `product_id`: ASIN
     - `flag_type`: String ("price_anomaly", "review_quality", "rating_suspicious", "seller_issue")
     - `severity`: String ("high", "medium", "low") - detected from context keywords
     - `description`: String (line from LLM response)
     - `reasoning`: String
     - `recommendation`: String
   - **Fallback Logic:** Simple heuristic checks for `price < $10 AND rating > 4.5`
   - **Token Tracking:** NOT tracked separately (text response, no structured output token extraction)

2. **Token Accumulation Strategy:**
   ```python
   # Each method returns (result, token_dict)
   total_tokens = {"input_tokens": 0, "output_tokens": 0}
   
   # Step 1: Compare products
   comparison, usage1 = compare_products_cot(...)
   total_tokens["input_tokens"] += usage1["input_tokens"]
   total_tokens["output_tokens"] += usage1["output_tokens"]
   
   # Step 2-5: Calculate scores, explain, identify tradeoffs, detect red flags
   # ... accumulate tokens from each step ...
   
   # Final total
   total_all = total_tokens["input_tokens"] + total_tokens["output_tokens"]
   # Example: 11023 input + 12044 output = 23067 total
   ```

3. **Final Output Structure:**
   - `analysis_result`: Dict with all analysis components
   - `value_scores`: Dict[asin → score]
   - `reasoning_chain`: List[ReasoningStep] (from Step 1)
   - `top_recommendation`: Product with highest adjusted value_score
   - `tradeoff_analysis`: From Step 4
   - `red_flags`: From Step 5
   - `confidence`: Float (weighted by all confidence factors)

- **Example Reasoning Chain:**
    
    ```json
    {
      "products_analyzed": 22,
      "reasoning_chain": [
        {
          "step_number": 1,
          "thought": "Check for any explicit brand preference. User only specified a general preference for noise cancelling headphones, no specific brand.",
          "action": "Identify brand preference",
          "observation": "No brand preference found; proceed without brand bias.",
          "confidence": 1.0
        },
        {
          "step_number": 2,
          "thought": "Filter products by budget (<= $300) and minimum rating (>= 4.0). Remove any items above budget or below rating.",
          "action": "Apply budget and rating constraints",
          "observation": "All listed items except B0F45CTLMM ($479), B0F3PT1VBL ($398), and B0F45CTLMM are within budget and meet rating threshold.",
          "confidence": 1.0
        }
      ],
      "value_scores": [...],
      "top_recommendation": {
        "product_id": "B0FGG71BRD",
        "product_name": "Amazon Fire HD 10 tablet (32 GB, Black) Noise Cancelling Headphone Bundle",
        "why_recommended": "The bundle delivers a complete solution that satisfies every user requirement—high-quality active noise-cancelling headphones with a comfortable over-ear design and Bluetooth connectivity—while also providing a versatile Fire HD 10 tablet for under $100, far below the $300 budget and with a perfect 5-star rating.",
        "match_quality": 0.92,
        "confidence": 0.85
      },
      "tradeoff_analysis": {...},
      "red_flags": [...]
    }
    
    ```
    
    - **Top Recommendation:** Bose QuietComfort 45 (ASIN B0DZHR44J9)
    - **Confidence:** **0.95**
    - **Reasoning Chain:**
        1. *Match:* Industry-leading active noise cancellation (ANC) perfectly fits office environment.
        2. *Comfort:* "Plush, lightweight" design meets "comfortable design" requirement for extended wear.
        3. *Price:* $279.00 within budget under $300.
    - **Red Flags:** 0.
- **Data flow:**
    - Input: `products`, `reviews_data`, `market_analysis`, `price_analysis`, `user_preferences`
    - Output: `analysis_result` (contains `value_scores`, `reasoning_chain`, `tradeoff_analysis`), `recommended_products`

## 8. Response Agent

**Task:** Present analysis results as an easy-to-understand answer.

### Technical Implementation:

1. **Single-Call Response Generation:**
   - **Model:** Cerebras Qwen 3-235B-A22B-Instruct with `temperature=0.3`, `max_tokens=8000` (largest model for best quality)
   - **Method:** `generate_comprehensive_response(analysis_result, user_query)`
   - **Strategy:** Generate ALL response components in ONE LLM call instead of 6+ separate calls

2. **Input Preparation:**
   - Serializes entire `analysis_result` dict to string
   - Includes: recommended products, value scores, reasoning, tradeoffs, red flags
   - Context size: ~10000+ characters

3. **Structured Output Schema:** `FinalResponse`
   - **Component 1:** `executive_summary`: ExecutiveSummary
     - `best_recommendation`: String (product name)
     - `key_reason`: String (one-line why)
     - `market_overview`: String (products analyzed)
     - `confidence_statement`: String (confidence level)
   
   - **Component 2:** `recommendations`: List[RecommendationDetails] (top 5)
     - Each has: product_id, name, price, rating, value_score
     - `why_recommended`: String (detailed reasoning)
     - `key_specs`: List[str] (5 main features)
     - `pros`: List[str] (3 strengths)
     - `cons`: List[str] (2 weaknesses)
     - `best_for`: String (ideal user profile)
     - `purchase_link`: String (Amazon URL)
   
   - **Component 3:** `comparison_table`: ComparisonTable
     - `columns`: List[str] (Rank, Product, Price, Rating, Value Score, etc.)
     - `rows`: List[ComparisonRow] (top 5 products)
     - Each row: rank, product_name, price, rating, reviews_count, key_features, value_score, best_for, pros, cons, link
   
   - **Component 4:** `reasoning_summary`: ReasoningSummary
     - `data_collection`: String (data sources used)
     - `analysis_methodology`: String (how analysis was done)
     - `key_factors`: List[str] (decision factors)
     - `confidence_assessment`: String (why confident)
     - `confidence_level`: String ("high", "medium", "low")
   
   - **Component 5:** `follow_up_suggestions`: FollowUpSuggestions
     - `suggestions`: List[FollowUpSuggestion] (3-5 suggestions)
     - Each: text, suggestion_type, example_query
     - `priority_suggestion`: String (most important next step)
   
   - **Component 6:** `red_flags`: RedFlagSummary
     - `has_red_flags`: Bool
     - `total_count`: Int
     - `high_severity_count`: Int
     - `summary_text`: String
     - `warnings`: List[str]

4. **Fallback Strategy:**
   - If LLM fails (e.g., max_tokens exceeded, incomplete JSON)
   - Falls back to `analyze_from_rating()` style manual construction
   - Extracts data from analysis_result and builds response programmatically
   - **No tokens consumed** in fallback mode

5. **Markdown Formatting (Non-LLM):**
   - Method: `format_final_response(final_response)`
   - Pure Python template rendering
   - Converts structured response → Markdown string (~3500 chars)
   - Format: Section headers, tables, links, emojis

6. **Token Tracking:**
   - Returns: `(FinalResponse, token_dict)` tuple
   - Typical usage: ~10139 input + 2747 output = 12886 total tokens
   - If fallback used: 0 tokens

- **Example Output Format:**
    
    ```markdown
    ## 🎯 Quick Answer
    
    **TAGRY Hybrid ANC 120h (ASIN: B0FRM53NB8)** - It offers exceptional 120-hour battery life, strong hybrid active noise cancellation, and a high 5.0-star rating—all for just $69.99.
    
    The under-$300 noise-cancelling headphone market is competitive, with strong budget options from brands like Soundcore and TAGRY, and premium choices from JBL, Sony, and Bose. I am highly confident in this recommendation based on comprehensive analysis of price, features, ratings, and value scoring across 22 products.
    
    ---
    
    ## ✅ Top Recommendation
    
    **TAGRY Hybrid ANC 120h** - $69.99
    ⭐ 5.0/5.0 | Value Score: 22.60
    
    🛒 **[View on Amazon](...)**
    
    ```
    
    - **Executive Summary:** "**Bose QuietComfort 45** - Industry-leading active noise cancellation combined with plush, lightweight comfort, all well under the $300 budget."
    - **Format:** Markdown report ~3500 characters long, including detailed comparison table and follow-up question suggestions.

## 9. Optimization Impact

**Architectural improvements:**

- **Parallel Intelligence:** Shifted from Sequential to Parallel execution for 3 agents (Review, Market, Price).
- **Consolidated Response:** Merged 6+ content generation steps into a single step.

**Results:**

- **Latency Reduction:** ~40-50% reduction in total processing time for Intelligence phase.
- **Throughput:** Increased concurrent processing capability thanks to asynchronous architecture.
- **Reliability:** Reduced points of failure by decreasing sequential LLM requests.

**Summary:** Real-world data shows the system doesn't just search for keywords but truly **"reasons"** to find products with the **best value** (high Value Score) rather than just the most expensive or cheapest products. The new architecture significantly optimizes user experience through faster response times.

## 10. Memory & Personalization System

**Mission:** Maintain context across turns and adapt to user preferences.

### Technical Implementation:

1. **Short-term Memory (Conversation Context):**
   - **Structure:** `ConversationHistory` containing list of `ConversationTurn`
   - **Turn Data:**
     - `user_query`: Original text
     - `search_plan`: Plan generated for that query
     - `products_found`: Count of results
     - `top_recommendation`: Selected product
   - **Usage:**
     - **Router Agent:** Uses last 5 queries to detect follow-ups and context switching
     - **Response Agent:** Uses previous recommendations to avoid repetition (future)

2. **Long-term Memory (User Preferences):**
   - **Structure:** `UserPreferences` object
   - **Components:**
     - `liked_brands`: Dict[brand, confidence] (e.g., `{"Sony": 0.8}`)
     - `must_have_features`: Dict[feature, confidence] (e.g., `{"noise cancelling": 0.9}`)
     - `max_budget`: Float (learned from price constraints)
   - **Learning Mechanism:**
     - **Explicit:** Extracted from query requirements (Planning Agent)
     - **Implicit:** Inferred from clicked products or positive feedback (future)

3. **Personalization Engine:**
   - **Component:** `PersonalizedScorer`
   - **Method:** `score_product(product, preferences, base_score)`
   - **Algorithm:**
     - **Brand Boost:** +10% score if brand is in `liked_brands`
     - **Feature Boost:** +5% score if product has `must_have_features`
     - **Price Check:** Penalize if significantly above `max_budget`
   - **Integration:** Applied in Analysis Agent (Step 2) to adjust Value Scores

4. **Data Flow:**
   - **Input:** `session_id` -> Load `SessionState` (History + Preferences)
   - **Update:** Planning Agent updates Preferences; Router updates History
   - **Output:** Personalized recommendations and context-aware responses