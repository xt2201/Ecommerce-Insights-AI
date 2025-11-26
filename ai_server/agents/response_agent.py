"""Response Agent - Enhanced Response Generation with Reasoning."""

import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.response_models import (
    ExecutiveSummary,
    RecommendationDetails,
    ComparisonTable,
    ComparisonRow,
    ReasoningSummary,
    FollowUpSuggestions,
    FollowUpSuggestion,
    RedFlagSummary,
    FinalResponse,
    ResponseGenerationResult,
)
from ai_server.utils.prompt_loader import load_prompt
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.utils.token_counter import extract_token_usage
from ai_server.utils.logger import get_agent_logger

logger = get_agent_logger()


class ResponseAgent:
    """Response Agent with enhanced formatting and reasoning summaries."""
    
    def __init__(self):
        """Initialize Response Agent."""
        # Use agent-specific LLM configuration
        self.llm = get_llm(agent_name="response")
        
        # Load prompts from ai_server/prompts directory
        prompt_dir = Path(__file__).parent.parent / "prompts"
        self.prompts = self._load_prompts(prompt_dir / "response_agent_prompts")
        
        logger.info("Response Agent initialized")
    
    def _load_prompts(self, prompt_file: Path) -> Dict[str, str]:
        """Load all prompts from response_agent_prompts.md."""
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
    
    def _extract_token_usage(self, raw_response) -> dict:
        """Extract token usage from LLM response."""
        tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
            tokens["input_tokens"] = raw_response.usage_metadata.get("input_tokens", 0)
            tokens["output_tokens"] = raw_response.usage_metadata.get("output_tokens", 0)
            tokens["total_tokens"] = tokens["input_tokens"] + tokens["output_tokens"]
        return tokens
    
    def generate_executive_summary(
        self,
        analysis_result: Dict[str, Any],
        user_query: str
    ) -> tuple[ExecutiveSummary, Dict[str, int]]:
        """Generate concise executive summary.
        
        Args:
            analysis_result: Complete analysis result
            user_query: Original user query
            
        Returns:
            Tuple of (ExecutiveSummary, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(ExecutiveSummary, include_raw=True)
            
            # Format analysis result
            analysis_str = self._format_analysis_for_summary(analysis_result)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["generate_response_summary"].format(
                    analysis_result=analysis_str,
                    user_query=user_query
                ))
            ]
            
            result = structured_llm.invoke(messages)
            summary = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"generate_executive_summary tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
            
            logger.info("Executive summary generated")
            return summary, token_usage
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            
            # Fallback summary - use first recommended product
            recommended = analysis_result.get("recommended_products", [])
            product_name = recommended[0].get("title", "Product found") if recommended else "Product found"
            
            return ExecutiveSummary(
                best_recommendation=product_name,
                key_reason="Best match based on requirements",
                market_overview="Multiple options available at various price points",
                confidence_statement="Moderate confidence in recommendation"
            ), token_usage
    
    def create_recommendation_details(
        self,
        product: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> RecommendationDetails:
        """Create detailed recommendation information.
        
        Args:
            product: Recommended product
            analysis_result: Analysis result with reasoning
            
        Returns:
            RecommendationDetails
        """
        try:
            # Extract recommendation explanation from analysis
            rec_explanation = analysis_result.get("top_recommendation", {})
            
            # Get why_recommended - could be in recommendation_reasoning or top_recommendation
            why_recommended = (
                product.get("recommendation_reasoning") or 
                rec_explanation.get("why_recommended") or 
                "Best match for your requirements"
            )
            
            return RecommendationDetails(
                product_id=product.get("asin", "unknown"),
                product_name=product.get("title", "Unknown Product"),
                price=product.get("price"),  # Accept None
                rating=product.get("rating"),  # Accept None
                value_score=product.get("value_score", 0.0),
                why_recommended=why_recommended,
                key_specs=product.get("features", [])[:5],
                pros=rec_explanation.get("pros", ["Good value", "Highly rated"])[:5],
                cons=rec_explanation.get("cons", ["Check reviews"])[:3],
                best_for=str(rec_explanation.get("best_for", "General use")),
                purchase_link=product.get("link", "")
            )
            
        except Exception as e:
            logger.error(f"Error creating recommendation details: {e}")
            
            # Fallback details
            return RecommendationDetails(
                product_id=product.get("asin", "unknown"),
                product_name=product.get("title", "Product"),
                price=product.get("price"),  # Accept None
                rating=product.get("rating"),  # Accept None
                value_score=0.5,
                why_recommended="Matches requirements",
                key_specs=product.get("features", [])[:3],
                pros=["Available"],
                cons=["Limited information"],
                best_for="General use",
                purchase_link=product.get("link", "")
            )
    
    def create_comparison_table(
        self,
        products: List[Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> ComparisonTable:
        """Create comparison table for top products.
        
        Args:
            products: Top products to compare
            analysis_result: Analysis with value scores
            
        Returns:
            ComparisonTable
        """
        try:
            # Get value scores from analysis
            value_scores = analysis_result.get("value_scores", [])
            value_score_map = {vs["product_id"]: vs for vs in value_scores}
            
            # Create rows for top 5 products
            rows = []
            for i, product in enumerate(products[:5], 1):
                asin = product.get("asin", "unknown")
                value_data = value_score_map.get(asin, {})
                
                # Handle None values safely
                reviews = product.get("reviews_count")
                if reviews is None or not isinstance(reviews, (int, float)):
                    reviews = 0
                
                row = ComparisonRow(
                    rank=i,
                    product_name=self._truncate_name(product.get("title", "Unknown")),
                    price=product.get("price"),  # Accept None
                    rating=product.get("rating"),  # Accept None
                    reviews_count=int(reviews),
                    key_features=product.get("features", [])[:4],
                    value_score=value_data.get("overall_score", 0.5),
                    best_for=self._determine_best_for(product, value_data),
                    pros=value_data.get("strengths", ["Good option"])[:3],
                    cons=value_data.get("weaknesses", ["Check details"])[:3]
                )
                rows.append(row)
            
            return ComparisonTable(
                columns=[
                    "Rank", "Product", "Price", "Rating", "Reviews",
                    "Key Features", "Value Score", "Best For", "Pros", "Cons"
                ],
                rows=rows,
                notes=["Value scores calculated based on price, rating, features, and reviews"]
            )
            
        except Exception as e:
            logger.error(f"Error creating comparison table: {e}")
            
            # Minimal fallback table
            rows = []
            for i, product in enumerate(products[:3], 1):
                rows.append(ComparisonRow(
                    rank=i,
                    product_name=self._truncate_name(product.get("title", "Product")),
                    price=product.get("price"),  # Accept None
                    rating=product.get("rating"),  # Accept None
                    reviews_count=product.get("reviews_count", 0),
                    key_features=product.get("features", [])[:3],
                    value_score=0.5,
                    best_for="General use",
                    pros=["Available"],
                    cons=["Limited info"],
                    purchase_link=product.get("link", "")
                ))
            
            return ComparisonTable(
                columns=["Rank", "Product", "Price", "Rating", "Value Score"],
                rows=rows,
                notes=[]
            )
    
    def create_reasoning_summary(
        self,
        analysis_result: Dict[str, Any]
    ) -> tuple[ReasoningSummary, Dict[str, int]]:
        """Create summary explaining analysis methodology.
        
        Args:
            analysis_result: Complete analysis result
            
        Returns:
            Tuple of (ReasoningSummary, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(ReasoningSummary, include_raw=True)
            
            # Format reasoning chain
            reasoning_chain = analysis_result.get("reasoning_chain", [])
            value_scores = analysis_result.get("value_scores", [])
            tradeoffs = analysis_result.get("tradeoff_analysis", {})
            
            chain_str = self._format_reasoning_chain(reasoning_chain)
            scores_str = self._format_value_scores(value_scores)
            tradeoffs_str = str(tradeoffs)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["explain_reasoning_summary"].format(
                    reasoning_chain=chain_str,
                    value_scores=scores_str,
                    tradeoffs=tradeoffs_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            summary = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"create_reasoning_summary tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
            
            logger.info("Reasoning summary generated")
            return summary, token_usage
            
        except Exception as e:
            logger.error(f"Error creating reasoning summary: {e}")
            
            # Fallback reasoning
            products_count = analysis_result.get("products_analyzed", 0)
            confidence = analysis_result.get("confidence", 0.5)
            
            conf_level = "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
            
            return ReasoningSummary(
                data_collection=f"Analyzed {products_count} products from Amazon search results.",
                analysis_methodology="Products scored based on price, rating, reviews count, and feature match. Chain-of-thought reasoning used to compare options and identify trade-offs.",
                key_factors=["Price", "Rating", "Reviews", "Features", "Value"],
                confidence_assessment=f"Confidence level is {conf_level} based on data quality and analysis completeness.",
                confidence_level=conf_level
            ), token_usage
    
    def generate_follow_up_suggestions(
        self,
        user_query: str,
        recommended_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]]
    ) -> FollowUpSuggestions:
        """Generate follow-up suggestions.
        
        Args:
            user_query: Original query
            recommended_product: Top recommendation
            alternatives: Alternative products
            
        Returns:
            Tuple of (FollowUpSuggestions, token_usage dict)
        """
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(FollowUpSuggestions, include_raw=True)
            
            rec_str = self._format_single_product(recommended_product)
            alt_str = self._format_products_brief(alternatives)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["generate_follow_up_suggestions"].format(
                    user_query=user_query,
                    recommended_product=rec_str,
                    alternatives=alt_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            suggestions = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            token_usage = extract_token_usage(raw_response)
            logger.info(f"generate_follow_up_suggestions tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
            
            logger.info(f"Generated {len(suggestions.suggestions)} follow-up suggestions")
            return suggestions, token_usage
            
        except Exception as e:
            logger.error(f"Error generating follow-up suggestions: {e}")
            
            # Fallback suggestions
            return FollowUpSuggestions(
                suggestions=[
                    FollowUpSuggestion(
                        suggestion_type="refinement",
                        text="Would you like to see more budget-friendly options?",
                        example_query=""
                    ),
                    FollowUpSuggestion(
                        suggestion_type="related_search",
                        text="Looking for accessories or complementary products?",
                        example_query=""
                    ),
                    FollowUpSuggestion(
                        suggestion_type="alternative_scenario",
                        text="Want to prioritize quality over price?",
                        example_query=""
                    )
                ],
                priority_suggestion="Consider reviewing customer feedback on the top recommendation"
            ), token_usage
    
    def create_red_flags_summary(
        self,
        red_flags: List[Dict[str, Any]]
    ) -> RedFlagSummary:
        """Create user-friendly red flags summary.
        
        Args:
            red_flags: List of red flags from analysis
            
        Returns:
            RedFlagSummary
        """
        if not red_flags:
            return RedFlagSummary(
                has_red_flags=False,
                total_count=0,
                high_severity_count=0,
                summary_text="No significant red flags detected. Products appear legitimate.",
                warnings=[]
            )
        
        high_severity = [rf for rf in red_flags if rf.get("severity") == "high"]
        
        warnings = [
            f"⚠️ {rf.get('description', 'Issue detected')}" 
            for rf in red_flags[:5]  # Top 5 warnings
        ]
        
        summary_text = f"Found {len(red_flags)} potential concern(s). "
        if high_severity:
            summary_text += f"{len(high_severity)} require careful review. "
        summary_text += "Please verify product details before purchasing."
        
        return RedFlagSummary(
            has_red_flags=True,
            total_count=len(red_flags),
            high_severity_count=len(high_severity),
            summary_text=summary_text,
            warnings=warnings
        )
    
    def generate_comprehensive_response(
        self,
        analysis_result: Dict[str, Any],
        user_query: str
    ) -> tuple[FinalResponse, dict]:
        """Generate comprehensive response in a single LLM call.
        
        Args:
            analysis_result: Complete analysis result
            user_query: Original user query
            
        Returns:
            Tuple of (FinalResponse object, token_dict)
        """
        tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        try:
            structured_llm = self.llm.with_structured_output(FinalResponse, include_raw=True)
            
            # Format analysis result for prompt
            # We pass the entire analysis result as a string representation
            # This allows the LLM to see all details (scores, reasoning, etc.)
            analysis_str = str(analysis_result)
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=self.prompts["generate_comprehensive_response"].format(
                    user_query=user_query,
                    analysis_result=analysis_str
                ))
            ]
            
            result = structured_llm.invoke(messages)
            response = result["parsed"]
            raw_response = result["raw"]
            
            # Extract token usage
            tokens = self._extract_token_usage(raw_response)
            logger.info(f"generate_comprehensive_response tokens: {tokens['input_tokens']} input + {tokens['output_tokens']} output = {tokens['total_tokens']} total")
            
            return response, tokens
            
        except Exception as e:
            logger.error(f"Error generating comprehensive response: {e}")
            
            # Attempt to recover from failed generation if possible, or use manual fallback
            logger.info("Falling back to manual response construction from analysis result")
            
            # Extract data from analysis_result
            top_rec = analysis_result.get("top_recommendation", {})
            recs = analysis_result.get("recommended_products", [])
            
            # 1. Executive Summary
            summary = ExecutiveSummary(
                best_recommendation=top_rec.get("title", "Product"),
                key_reason=top_rec.get("recommendation_reasoning", "Best match for your needs"),
                market_overview=f"Analyzed {len(recs)} options",
                confidence_statement="Generated via fallback mechanism"
            )
            
            # 2. Recommendations
            recommendations = []
            for p in recs[:5]:
                recommendations.append(RecommendationDetails(
                    product_id=p.get("asin", "unknown"),
                    product_name=p.get("title", "Unknown"),
                    price=p.get("price"),
                    rating=p.get("rating"),
                    value_score=p.get("value_score", 0.0),
                    why_recommended=p.get("recommendation_reasoning", "Recommended option"),
                    key_specs=p.get("features", [])[:5],
                    pros=p.get("pros", ["Good option"])[:3],
                    cons=p.get("cons", [])[:2],
                    best_for=str(p.get("best_for", "General use")),
                    purchase_link=p.get("link", "")
                ))
            
            # 3. Comparison Table
            rows = []
            for i, p in enumerate(recs[:5], 1):
                rows.append(ComparisonRow(
                    rank=i,
                    product_name=p.get("title", "Unknown")[:30] + "...",
                    price=p.get("price"),
                    rating=p.get("rating"),
                    reviews_count=p.get("reviews_count", 0),
                    key_features=p.get("features", [])[:3],
                    value_score=p.get("value_score", 0.0),
                    best_for=str(p.get("best_for", "General use")),
                    pros=p.get("pros", [])[:2],
                    cons=p.get("cons", [])[:2],
                    purchase_link=p.get("link", "")
                ))
            
            table = ComparisonTable(
                columns=["Rank", "Product", "Price", "Rating", "Value Score"],
                rows=rows,
                notes=["Generated via fallback"]
            )
            
            # 4. Reasoning
            reasoning = ReasoningSummary(
                data_collection="Fallback analysis",
                analysis_methodology="Manual extraction from analysis results",
                key_factors=["Price", "Rating"],
                confidence_assessment="Low (Fallback)",
                confidence_level="low"
            )
            
            # 5. Suggestions
            suggestions = FollowUpSuggestions(
                suggestions=[
                    FollowUpSuggestion(text="Refine your search?", suggestion_type="refinement", example_query=""),
                    FollowUpSuggestion(text="Check details?", suggestion_type="related_search", example_query="")
                ],
                priority_suggestion="Check product details"
            )
            
            # 6. Red Flags
            red_flags = RedFlagSummary(
                has_red_flags=False,
                total_count=0,
                high_severity_count=0,
                summary_text="",
                warnings=[]
            )
            
            return FinalResponse(
                executive_summary=summary,
                recommendations=recommendations,
                comparison_table=table,
                reasoning_summary=reasoning,
                follow_up_suggestions=suggestions,
                red_flags=red_flags
            ), tokens  # Return tokens (will be zeros for fallback)

    def format_final_response(
        self,
        final_response: FinalResponse
    ) -> str:
        """Format final response as markdown.
        
        Args:
            final_response: Complete response structure
            
        Returns:
            Formatted markdown string
        """
        try:
            summary = final_response.executive_summary
            top_rec = final_response.recommendations[0] if final_response.recommendations else None
            table = final_response.comparison_table
            reasoning = final_response.reasoning_summary
            suggestions = final_response.follow_up_suggestions
            red_flags = final_response.red_flags
            
            # Check if we have a recommendation
            if not top_rec:
                logger.warning("No recommendations available in final response")
                return "# No Recommendations Available\n\nUnable to generate recommendations at this time."
            
            # Safe format helpers
            def safe_price(price):
                return f"${price:.2f}" if price is not None else "N/A"
            
            def safe_rating(rating):
                return f"{rating:.1f}/5.0" if rating is not None else "N/A"
            
            def safe_value_score(score):
                return f"{score:.2f}" if score is not None else "N/A"
            
            # Build markdown
            lines = [
                "## 🎯 Answer\n",
                f"**{summary.best_recommendation}** - {summary.key_reason}\n",
                f"{summary.market_overview} {summary.confidence_statement}\n",
                "---\n",
                "## ✅ Top Recommendation\n",
                f"**{top_rec.product_name}** - {safe_price(top_rec.price)}",
                f"⭐ {safe_rating(top_rec.rating)} | Value Score: {safe_value_score(top_rec.value_score)}\n",
            ]
            
            # Add purchase link if available
            if top_rec.purchase_link:
                lines.append(f"🛒 **[View on Amazon]({top_rec.purchase_link})**\n")
            
            lines.extend([
                f"**Why This Product:**",
                f"{top_rec.why_recommended}\n",
                f"**Best For:** {top_rec.best_for}\n",
                "**Pros:**"
            ])
            
            for pro in top_rec.pros:
                lines.append(f"- ✓ {pro}")
            
            lines.append("\n**Cons:**")
            for con in top_rec.cons:
                lines.append(f"- ✗ {con}")
            
            lines.extend([
                "\n---\n",
                "## 📊 Top Options Comparison\n",
                "| Rank | Product | Price | Rating | Value Score | Link |",
                "|------|---------|-------|--------|-------------|------|"
            ])
            
            for row in table.rows:
                # Format link (handle empty links)
                link_text = f"[View]({row.purchase_link})" if row.purchase_link else "N/A"
                
                lines.append(
                    f"| {row.rank} | {row.product_name[:40]} | {safe_price(row.price)} | "
                    f"{safe_rating(row.rating)} | {safe_value_score(row.value_score)} | {link_text} |"
                )
            
            lines.extend([
                "\n---\n",
                "## 🔍 How We Analyzed\n",
                f"**Data:** {reasoning.data_collection}\n",
                f"**Method:** {reasoning.analysis_methodology}\n",
                f"**Confidence:** {reasoning.confidence_level.upper()} - {reasoning.confidence_assessment}\n",
                "---\n"
            ])
            
            if red_flags.has_red_flags:
                lines.extend([
                    "## ⚠️ Things to Watch Out For\n",
                    red_flags.summary_text + "\n"
                ])
                for warning in red_flags.warnings:
                    lines.append(f"- {warning}")
                lines.append("\n---\n")
            
            lines.extend([
                "## 💡 What's Next?\n"
            ])
            
            for sug in suggestions.suggestions:
                lines.append(f"- {sug.text}")
            
            if suggestions.priority_suggestion:
                lines.append(f"\n**Recommended:** {suggestions.priority_suggestion}")
            
            lines.extend([
                "\n---\n",
                f"*Confidence: {reasoning.confidence_level}* | "
                f"*Analysis Date: {datetime.now().strftime('%Y-%m-%d')}*"
            ])
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting final response: {e}", exc_info=True)
            top_name = final_response.recommendations[0].product_name if final_response.recommendations else "N/A"
            return f"# Response Generated\n\nTop recommendation: {top_name}"


def generate_response(state: AgentState) -> AgentState:
    """Main Response Agent function.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with final response
    """
    logger.info("=== Response Agent Starting ===")
    start_time = time.time()
    
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create response step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.RESPONSE,
            agent_name="response_agent"
        )
    
    try:
        agent = ResponseAgent()
        
        # Get analysis result
        analysis_result = state.get("analysis_result", {})
        if not analysis_result:
            logger.warning("No analysis result available")
            state["response_error"] = "No analysis result to format"
            
            # Fail step
            if trace_id and step:
                trace_manager.fail_step(
                    trace_id=trace_id,
                    step_id=step.step_id,
                    error="No analysis result to format"
                )
            
            return state
        
        # Get products and query
        products = state.get("products", [])
        user_query = state.get("original_query", "") or state.get("user_query", "")
        
        if not products:
            logger.warning("No products to format response")
            state["response_error"] = "No products available"
            
            # Fail step
            if trace_id and step:
                trace_manager.fail_step(
                    trace_id=trace_id,
                    step_id=step.step_id,
                    error="No products available"
                )
            
            return state
        
        logger.info("Generating comprehensive response (Optimized Single Call)...")
        
        # Generate comprehensive response in one go
        final_response, total_tokens = agent.generate_comprehensive_response(analysis_result, user_query)
        
        # Format as markdown
        logger.info("Formatting final response")
        formatted_response = agent.format_final_response(final_response)
        final_response.formatted_markdown = formatted_response
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Create result
        result = ResponseGenerationResult(
            success=True,
            final_response=final_response,
            generation_time=generation_time,
            tokens_used=total_tokens.get("total_tokens", 0),
            errors=[]
        )
        
        # Update state
        state["final_response"] = final_response.model_dump()
        state["formatted_response"] = formatted_response
        state["response_generation_result"] = result.model_dump()
        
        logger.info(f"Response generation complete in {generation_time:.2f}s")
        logger.info(f"Response length: {len(formatted_response)} characters")
        logger.info(f"Total tokens used: {total_tokens}")
        
        # Complete step with success and actual token usage
        if trace_id and step:
            total = total_tokens.get("total_tokens", 0)
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={
                    "response_length": len(formatted_response),
                    "generation_time": generation_time,
                    "products_count": len(products),
                    "success": True
                },
                token_usage=TokenUsage(
                    prompt_tokens=total_tokens.get("input_tokens", 0),
                    completion_tokens=total_tokens.get("output_tokens", 0),
                    total_tokens=total
                )
            )
        
        return state
        
    except Exception as e:
        logger.error(f"Error in Response Agent: {e}", exc_info=True)
        state["response_error"] = str(e)
        
        # Fail step on error
        if trace_id and step:
            trace_manager.fail_step(
                trace_id=trace_id,
                step_id=step.step_id,
                error=str(e)
            )
        
        return state
