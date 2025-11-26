"""Analysis Agent - Chain-of-Thought Reasoning for Product Analysis."""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.memory.personalized_scorer import PersonalizedScorer
from ai_server.schemas.analysis_models import (
    ProductComparison,
    ValueScore,
    RecommendationExplanation,
    TradeoffAnalysis,
    RedFlag,
    AnalysisResult,
    ReasoningStep,
)
from ai_server.utils.prompt_loader import load_prompt
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.utils.token_counter import extract_token_usage

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Analysis Agent with chain-of-thought reasoning capabilities."""
    
    def __init__(self):
        """Initialize Analysis Agent."""
        # Use agent-specific LLM configuration
        self.llm = get_llm(agent_name="analysis")
        
        # Load prompts from ai_server/prompts directory
        prompt_dir = Path(__file__).parent.parent / "prompts"
        self.prompts = self._load_prompts(prompt_dir / "analysis_agent_prompts")
        
        logger.info("Analysis Agent initialized with chain-of-thought reasoning")
    
    def _load_prompts(self, prompt_file: Path) -> Dict[str, str]:
        """Load all prompts from analysis_agent_prompts.md."""
        content = load_prompt(str(prompt_file))
        
        # Parse prompts by headers
        prompts = {}
        current_key = None
        current_content = []
        
        for line in content.split("\n"):
            if line.startswith("## "):
                if current_key:
                    prompts[current_key] = "\n".join(current_content).strip()
                current_key = line.replace("## ", "").strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)
        
        # Save last prompt
        if current_key:
            prompts[current_key] = "\n".join(current_content).strip()
        
        return prompts
    
    def compare_products_cot(
        self,
        products: List[Dict[str, Any]],
        user_needs: Dict[str, Any]
    ) -> tuple[ProductComparison, Dict[str, int]]:
        """Compare products using chain-of-thought reasoning.
        
        Args:
            products: List of products to compare
            user_needs: User requirements and preferences
            
        Returns:
            Tuple of (ProductComparison with step-by-step reasoning, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            # Create structured output LLM with token tracking
            structured_llm = self.llm.with_structured_output(ProductComparison, include_raw=True)
            
            # Format products for comparison
            products_str = self._format_products_for_analysis(products)
            needs_str = self._format_user_needs(user_needs)
            
            # Create messages
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["compare_products_cot"].format(
                    products=products_str,
                    user_needs=needs_str
                ))
            ]
            
            # Get comparison with reasoning and token info
            result = structured_llm.invoke(messages)
            comparison = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"compare_products_cot tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
            
            logger.info(f"Product comparison completed with {len(comparison.reasoning_chain)} reasoning steps")
            return comparison, token_usage
            
        except Exception as e:
            logger.error(f"Error in compare_products_cot: {e}")
            
            from ai_server.schemas.analysis_models import ListValue
            
            # Fallback comparison
            return ProductComparison(
                products_compared=[p.get("asin", "unknown") for p in products[:3]],
                reasoning_chain=[
                    ReasoningStep(
                        step_number=1,
                        thought="Error occurred during comparison",
                        action="Using fallback comparison",
                        observation="Limited analysis available",
                        confidence=0.3
                    )
                ],
                differentiating_features=[],
                value_rankings="[]",
                trade_offs="{}",
                recommendation="Unable to complete detailed comparison due to error",
                confidence=0.3
            ), token_usage
    
    def calculate_value_score_reasoning(
        self,
        product: Dict[str, Any],
        user_needs: Dict[str, Any]
    ) -> tuple[ValueScore, Dict[str, int]]:
        """Calculate value score with transparent reasoning.
        
        Args:
            product: Product to score
            user_needs: User requirements
            
        Returns:
            Tuple of (ValueScore with reasoning explanation, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(ValueScore, include_raw=True)
            
            product_str = self._format_single_product(product)
            needs_str = self._format_user_needs(user_needs)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["calculate_value_score_reasoning"].format(
                    product=product_str,
                    user_needs=needs_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            value_score = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"calculate_value_score tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out")
            
            # Debug: Log raw response if parsing failed
            if value_score is None:
                logger.warning(
                    f"LLM failed to parse ValueScore for {product.get('title', '')[:50]}\n"
                    f"Raw response type: {type(raw_response)}\n"
                    f"Raw content preview: {str(raw_response.content if hasattr(raw_response, 'content') else raw_response)[:200]}"
                )
            
            # Check if LLM failed to parse (returned None)
            if value_score is None:
                logger.warning(f"LLM returned None for value score, using fallback for {product.get('title', '')[:50]}")
                raise ValueError("Parsed value score is None")
            
            # Safe format for overall_score (handle None)
            score_val = value_score.overall_score if value_score.overall_score is not None else 0.0
            logger.info(f"Value score calculated: {score_val:.2f} for {product.get('title', 'unknown')}")
            return value_score, token_usage
            
        except Exception as e:
            logger.error(f"Error calculating value score: {e}")
            
            # Simple fallback scoring (handle None values)
            rating = product.get("rating") or 0.0
            reviews_count = product.get("reviews_count") or 0
            price = product.get("price") or 0.0  # Treat None as 0 for calculation
            
            from ai_server.schemas.analysis_models import FloatValue
            
            # Basic heuristic (with None-safe calculations)
            rating_score = (rating / 5.0) if rating else 0.0
            reviews_score = min(reviews_count / 1000, 1.0) if reviews_count else 0.0
            price_score = (1 - min(price / 500, 1.0)) if price else 0.0
            score = rating_score * 0.4 + reviews_score * 0.3 + price_score * 0.3
            
            return ValueScore(
                product_id=product.get("asin", "unknown"),
                overall_score=min(max(score, 0.0), 1.0),
                component_scores=[
                    FloatValue(key="rating", value=rating_score),
                    FloatValue(key="reviews", value=reviews_score),
                    FloatValue(key="price", value=price_score)
                ],
                reasoning="Fallback scoring: weighted average of rating, reviews, and price",
                strengths=[],
                weaknesses=[],
                confidence=0.4
            ), token_usage
    
    def explain_recommendation(
        self,
        product: Dict[str, Any],
        user_needs: Dict[str, Any],
        alternatives: List[Dict[str, Any]]
    ) -> tuple[RecommendationExplanation, Dict[str, int]]:
        """Generate detailed explanation for recommendation.
        
        Args:
            product: Recommended product
            user_needs: User requirements
            alternatives: Other products considered
            
        Returns:
            Tuple of (RecommendationExplanation with pros/cons and reasoning, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(RecommendationExplanation, include_raw=True)
            
            product_str = self._format_single_product(product)
            needs_str = self._format_user_needs(user_needs)
            alternatives_str = self._format_products_for_analysis(alternatives)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["explain_recommendation"].format(
                    recommended_product=product_str,
                    user_needs=needs_str,
                    alternatives=alternatives_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            explanation = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"explain_recommendation tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out")
            
            logger.info(f"Recommendation explanation generated for {product.get('title', 'unknown')}")
            return explanation, token_usage
            
        except Exception as e:
            logger.error(f"Error generating recommendation explanation: {e}")
            
            from ai_server.schemas.analysis_models import FloatValue
            
            return RecommendationExplanation(
                product_id=product.get("asin", "unknown"),
                product_name=product.get("title", "Unknown Product"),
                why_recommended="Product matches basic requirements",
                match_quality=0.5,
                satisfied_needs=["basic requirements"],
                value_proposition="Good balance of features and price",
                pros=["Available", "Meets requirements"],
                cons=["Limited analysis available"],
                alternatives_considered=[],
                confidence_breakdown=[FloatValue(key="overall", value=0.5)],
                overall_confidence=0.5
            ), token_usage
    
    def identify_tradeoffs(
        self,
        products: List[Dict[str, Any]],
        user_needs: Dict[str, Any]
    ) -> tuple[TradeoffAnalysis, Dict[str, int]]:
        """Identify tradeoffs between different products.
        
        Args:
            products: Products to analyze
            user_needs: User requirements
            
        Returns:
            Tuple of (TradeoffAnalysis with budget/quality/features analysis, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(TradeoffAnalysis, include_raw=True)
            
            products_str = self._format_products_for_analysis(products)
            needs_str = self._format_user_needs(user_needs)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["identify_tradeoffs"].format(
                    products=products_str,
                    user_needs=needs_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            tradeoffs = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"identify_tradeoffs tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out")
            
            logger.info("Tradeoff analysis completed")
            return tradeoffs, token_usage
            
        except Exception as e:
            logger.error(f"Error identifying tradeoffs: {e}")
            
            # Fallback: simple price-based categorization (handle None prices)
            sorted_products = sorted(products, key=lambda p: (p.get("price") or 0))
            
            from ai_server.schemas.analysis_models import StringValue
            
            return TradeoffAnalysis(
                comparison_pairs="[]",
                budget_vs_quality="Lower-priced options may have fewer features or lower ratings",
                features_vs_price="Higher-priced products typically offer more features",
                brand_vs_value="Consider whether brand premium provides value",
                recommendations=[
                    StringValue(key="budget_conscious", value="Choose lower-priced options"),
                    StringValue(key="quality_focused", value="Choose higher-rated products"),
                    StringValue(key="balanced", value="Choose mid-range products")
                ],
                best_budget=sorted_products[0].get("asin", "unknown") if sorted_products else "unknown",
                best_value=sorted_products[len(sorted_products)//2].get("asin", "unknown") if sorted_products else "unknown",
                best_premium=sorted_products[-1].get("asin", "unknown") if sorted_products else "unknown"
            ), token_usage
    
    def detect_red_flags(
        self,
        products: List[Dict[str, Any]]
    ) -> List[RedFlag]:
        """Detect red flags in products (suspicious reviews, pricing, etc).
        
        Args:
            products: Products to check
            
        Returns:
            List of RedFlag objects
        """
        try:
            # Use LLM to analyze products for red flags
            products_str = self._format_products_for_analysis(products)
            
            # Create prompt
            prompt = self.prompts["detect_red_flags"].format(products=products_str)
            
            # Get LLM response (as text, will parse manually)
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse response to create RedFlag objects
            red_flags = self._parse_red_flags_from_response(response.content, products)
            
            logger.info(f"Detected {len(red_flags)} red flags")
            return red_flags
            
        except Exception as e:
            logger.error(f"Error detecting red flags: {e}")
            
            # Fallback: simple heuristic checks
            red_flags = []
            
            for product in products:
                # Check for suspiciously low price + high rating (handle None values)
                price = product.get("price") or 0
                rating = product.get("rating") or 0
                
                if price and price < 10 and rating > 4.5:
                    red_flags.append(RedFlag(
                        product_id=product.get("asin", "unknown"),
                        flag_type="price_anomaly",
                        severity="medium",
                        description=f"Very low price (${price}) with high rating ({rating})",
                        reasoning="This combination may indicate quality concerns or fake reviews",
                        recommendation="Verify product legitimacy and read reviews carefully"
                    ))
            
            return red_flags
    
    def _parse_red_flags_from_response(
        self,
        response_text: str,
        products: List[Dict[str, Any]]
    ) -> List[RedFlag]:
        """Parse LLM response to extract red flags."""
        red_flags = []
        
        # Simple parsing: look for keywords and patterns
        lines = response_text.split("\n")
        current_product = None
        
        for line in lines:
            # Try to identify product
            for product in products:
                asin = product.get("asin", "")
                title = product.get("title", "")
                if asin in line or title[:30] in line:
                    current_product = product
                    break
            
            # Look for red flag indicators
            line_lower = line.lower()
            
            if any(word in line_lower for word in ["suspicious", "fake", "concern", "warning"]):
                if current_product:
                    # Determine flag type and severity from context
                    flag_type = "review_quality"
                    severity = "medium"
                    
                    if "price" in line_lower:
                        flag_type = "price_anomaly"
                    elif "seller" in line_lower:
                        flag_type = "seller_issue"
                    elif "rating" in line_lower:
                        flag_type = "rating_suspicious"
                    
                    if "high" in line_lower or "serious" in line_lower:
                        severity = "high"
                    elif "minor" in line_lower or "slight" in line_lower:
                        severity = "low"
                    
                    red_flags.append(RedFlag(
                        product_id=current_product.get("asin", "unknown"),
                        flag_type=flag_type,
                        severity=severity,
                        description=line.strip(),
                        reasoning="Pattern detected by analysis",
                        recommendation="Review carefully before purchase"
                    ))
        
        return red_flags
    
    def _format_products_for_analysis(self, products: List[Dict[str, Any]]) -> str:
        """Format products for LLM input."""
        formatted = []
        
        for i, product in enumerate(products, 1):
            formatted.append(f"Product {i}:")
            formatted.append(f"  ASIN: {product.get('asin', 'unknown')}")
            formatted.append(f"  Title: {product.get('title', 'N/A')}")
            formatted.append(f"  Price: ${product.get('price', 'N/A')}")
            formatted.append(f"  Rating: {product.get('rating', 'N/A')}/5.0")
            formatted.append(f"  Reviews: {product.get('reviews_count', 0)}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_single_product(self, product: Dict[str, Any]) -> str:
        """Format single product for LLM input."""
        lines = [
            f"ASIN: {product.get('asin', 'unknown')}",
            f"Title: {product.get('title', 'N/A')}",
            f"Price: ${product.get('price', 'N/A')}",
            f"Rating: {product.get('rating', 'N/A')}/5.0",
            f"Reviews: {product.get('reviews_count', 0)}"
        ]
        
        return "\n".join(lines)
    
    def _format_user_needs(self, user_needs: Dict[str, Any]) -> str:
        """Format user needs for LLM input."""
        lines = []
        
        if "requirements" in user_needs and user_needs["requirements"]:
            lines.append(f"Requirements: {', '.join(user_needs['requirements'])}")
        
        if "budget" in user_needs and user_needs["budget"]:
            lines.append(f"Budget: ${user_needs['budget']}")
        
        if "priorities" in user_needs and user_needs["priorities"]:
            lines.append(f"Priorities: {', '.join(user_needs['priorities'])}")
        
        if "preferences" in user_needs and user_needs["preferences"]:
            lines.append(f"Preferences: {user_needs['preferences']}")
        
        # Add brand preferences - IMPORTANT for brand-specific queries
        if "brand_preferences" in user_needs and user_needs["brand_preferences"]:
            brands = user_needs["brand_preferences"]
            lines.append(f"Preferred Brands: {', '.join(brands)}")
        
        # Add min rating if specified
        if "min_rating" in user_needs and user_needs["min_rating"]:
            lines.append(f"Minimum Rating: {user_needs['min_rating']}/5.0")
        
        return "\n".join(lines) if lines else "No specific requirements provided"


def analyze_products(state: AgentState) -> AgentState:
    """Main Analysis Agent function with chain-of-thought reasoning.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with analysis results
    """
    logger.info("=== Analysis Agent Starting ===")
    
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create analysis step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.ANALYSIS,
            agent_name="analysis_agent"
        )
    
    try:
        agent = AnalysisAgent()
        
        # Get products from collection phase
        products = state.get("products", [])
        if not products:
            logger.warning("No products to analyze")
            state["analysis_error"] = "No products available for analysis"
            
            # Fail step
            if trace_id and step:
                trace_manager.fail_step(
                    trace_id=trace_id,
                    step_id=step.step_id,
                    error="No products available for analysis"
                )
            
            return state
        
        logger.info(f"Analyzing {len(products)} products with chain-of-thought reasoning")
        
        # Extract user needs from search_plan (updated in planning agent)
        search_plan = state.get("search_plan", {})
        requirements = search_plan.get("requirements", {})
        
        user_needs = {
            "requirements": requirements.get("required_features", []),
            "budget": search_plan.get("max_price") or 1000,
            "priorities": requirements.get("required_features", []),
            "preferences": search_plan.get("keywords", [""])[0] if search_plan.get("keywords") else "",
            "brand_preferences": requirements.get("brand_preferences", []),
            "min_rating": requirements.get("min_rating")
        }
        
        # Token accumulator for all LLM calls
        total_input_tokens = 0
        total_output_tokens = 0
        
        # Step 1: Compare products with reasoning
        logger.info("Step 1: Comparing products with chain-of-thought")
        comparison, comp_tokens = agent.compare_products_cot(products, user_needs)
        total_input_tokens += comp_tokens.get("input_tokens", 0)
        total_output_tokens += comp_tokens.get("output_tokens", 0)
        
        # Step 2: Calculate value scores for top products
        logger.info("Step 2: Calculating value scores with reasoning")
        top_products = products[:5]  # Analyze top 5
        value_scores = []
        
        # Get user preferences for personalization
        user_preferences = state.get("user_preferences")
        
        for product in top_products:
            # Calculate base score with reasoning
            score, score_tokens = agent.calculate_value_score_reasoning(product, user_needs)
            total_input_tokens += score_tokens.get("input_tokens", 0)
            total_output_tokens += score_tokens.get("output_tokens", 0)
            
            # Skip if score calculation failed
            if score is None:
                logger.warning(f"Skipping product due to score calculation failure: {product.get('title', '')[:50]}")
                continue
            
            # Apply personalized scoring if preferences available
            # user_preferences is Dict[str, Any] now (not UserPreferences object)
            if user_preferences and isinstance(user_preferences, dict):
                confidence = user_preferences.get('confidence', 0.0)
                if confidence > 0.3:
                    base_score = score.overall_score if score.overall_score is not None else 0.5
                    personalized_score = PersonalizedScorer.score_product(
                        product,
                        user_preferences,
                        base_score
                    )
                    # Update score with personalization
                    score.overall_score = personalized_score
                    logger.debug(
                        f"Personalized score for {product.get('title', '')[:50]}: "
                        f"{base_score:.2f} → {personalized_score:.2f}"
                    )
            
            value_scores.append(score)
        
        # Sort by value score (now includes personalization)
        value_scores.sort(key=lambda x: x.overall_score if x.overall_score else 0, reverse=True)
        
        # Step 3: Explain recommendation for top product
        logger.info("Step 3: Generating recommendation explanation")
        top_product = products[0]  # Assuming first is best from collection
        alternatives = products[1:4]  # Next 3 as alternatives
        
        recommendation, rec_tokens = agent.explain_recommendation(
            top_product,
            user_needs,
            alternatives
        )
        total_input_tokens += rec_tokens.get("input_tokens", 0)
        total_output_tokens += rec_tokens.get("output_tokens", 0)
        
        # Step 4: Identify tradeoffs
        logger.info("Step 4: Analyzing tradeoffs")
        tradeoffs, tradeoff_tokens = agent.identify_tradeoffs(products, user_needs)
        total_input_tokens += tradeoff_tokens.get("input_tokens", 0)
        total_output_tokens += tradeoff_tokens.get("output_tokens", 0)
        
        # Step 5: Detect red flags (no LLM structured output, tokens tracked internally)
        logger.info("Step 5: Detecting red flags")
        red_flags = agent.detect_red_flags(products)
        
        # Log total token usage
        total_tokens = total_input_tokens + total_output_tokens
        logger.info(f"Analysis Agent total tokens: {total_input_tokens} in + {total_output_tokens} out = {total_tokens} total")
        
        # Aggregate intelligence data from state (parallel execution results)
        review_analysis = state.get("review_analysis")
        market_analysis = state.get("market_analysis")
        price_analysis = state.get("price_analysis")
        
        # Create final analysis result
        analysis_result = AnalysisResult(
            products_analyzed=len(products),
            reasoning_chain=comparison.reasoning_chain,
            value_scores=value_scores,
            top_recommendation=recommendation,
            tradeoff_analysis=tradeoffs,
            red_flags=red_flags,
            confidence=comparison.confidence,
            metadata={
                "agent_version": "1.0",
                "reasoning_type": "chain-of-thought",
                "user_needs": user_needs
            },
            review_analysis=review_analysis,
            market_analysis=market_analysis,
            price_analysis=price_analysis
        )
        
        # Update state
        # Update state (merge with existing analysis results from other agents)
        current_analysis = state.get("analysis_result", {})
        if not isinstance(current_analysis, dict):
            current_analysis = {}
            
        new_analysis = analysis_result.model_dump()
        current_analysis.update(new_analysis)
        
        state["analysis_result"] = current_analysis
        
        # Create recommended products list (top 3-5 based on value scores)
        recommended_products_list = []
        for i, score in enumerate(value_scores[:5]):  # Top 5
            product_id = score.product_id
            # Find matching product
            matching_product = next((p for p in products if p.get("asin") == product_id), None)
            if matching_product:
                recommended_products_list.append({
                    **matching_product,
                    "recommendation_reasoning": recommendation.why_recommended if i == 0 else f"Alternative option #{i+1}",
                    "value_score": score.overall_score
                })
        
        # Fallback: at least include top product
        if not recommended_products_list:
            recommended_products_list = [{
                **top_product,
                "recommendation_reasoning": recommendation.why_recommended,
                "value_score": value_scores[0].overall_score if value_scores else 0.0
            }]
        
        state["recommended_products"] = recommended_products_list
        
        logger.info(f"Analysis complete. Recommended {len(recommended_products_list)} products")
        logger.info(f"Top recommendation: {top_product.get('title', 'unknown')}")
        # Safe format for confidence (handle None)
        confidence_val = analysis_result.confidence if analysis_result.confidence is not None else 0.0
        logger.info(f"Confidence: {confidence_val:.2f}")
        logger.info(f"Red flags found: {len(red_flags)}")
        
        # Complete step with actual accumulated token usage
        if trace_id and step:
            total_all = total_input_tokens + total_output_tokens
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={
                    "products_analyzed": len(products),
                    "top_recommendation": top_product.get("title", "unknown"),
                    "confidence": analysis_result.confidence,
                    "red_flags_count": len(red_flags),
                    "value_scores_count": len(value_scores)
                },
                token_usage=TokenUsage(
                    prompt_tokens=total_input_tokens,
                    completion_tokens=total_output_tokens,
                    total_tokens=total_all
                )
            )
        
        return state
        
    except Exception as e:
        logger.error(f"Error in Analysis Agent: {e}", exc_info=True)
        state["analysis_error"] = str(e)
        
        # Fail step on error
        if trace_id and step:
            trace_manager.fail_step(
                trace_id=trace_id,
                step_id=step.step_id,
                error=str(e)
            )
        
        return state
