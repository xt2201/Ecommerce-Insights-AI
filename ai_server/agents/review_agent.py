"""Review Agent - Analyzes product reviews for sentiment and authenticity."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ai_server.schemas.agent_state import AgentState
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage

logger = logging.getLogger(__name__)


from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.utils.token_counter import extract_token_usage
from ai_server.schemas.analysis_models import ReviewAnalysis, AuthenticityCheck

class ReviewAgent:
    """Review Agent with LLM capabilities."""
    
    def __init__(self):
        self.llm = get_llm(agent_name="review")
        self.prompts = load_prompts_as_dict("review_agent_prompts")

    def analyze_reviews_cot(self, product_title: str, reviews: List[Dict[str, Any]]) -> tuple[ReviewAnalysis, dict]:
        """Analyze reviews using Chain of Thought."""
        try:
            structured_llm = self.llm.with_structured_output(ReviewAnalysis, include_raw=True)
            
            # Format reviews for prompt
            reviews_text = "\n".join([
                f"- {r.get('title', '')}: {r.get('text', '')[:200]}..." 
                for r in reviews[:10]  # Analyze top 10 reviews to save tokens
            ])
            
            prompt = self.prompts["analyze_sentiment"].format(
                product_title=product_title,
                reviews_text=reviews_text
            )
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=prompt)
            ]
            
            out = structured_llm.invoke(messages)
            parsed = out["parsed"]
            raw = out["raw"]
            usage = extract_token_usage(raw)
            
            return parsed, usage
            
        except Exception as e:
            logger.error(f"Error in analyze_reviews_cot: {e}")
            return ReviewAnalysis(
                summary="Error analyzing reviews",
                sentiment_score=0.5,
                pros=[],
                cons=[],
                aspect_sentiment={}
            ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def detect_fake_reviews(self, product_title: str, reviews: List[Dict[str, Any]]) -> tuple[AuthenticityCheck, dict]:
        """Detect fake reviews."""
        try:
            structured_llm = self.llm.with_structured_output(AuthenticityCheck, include_raw=True)
            
            reviews_text = "\n".join([
                f"- {r.get('title', '')} ({r.get('date', 'No date')}): {r.get('text', '')[:200]}..." 
                for r in reviews[:10]
            ])
            
            prompt = self.prompts["detect_fake_reviews"].format(
                product_title=product_title,
                reviews_text=reviews_text
            )
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=prompt)
            ]
            
            out = structured_llm.invoke(messages)
            parsed = out["parsed"]
            raw = out["raw"]
            usage = extract_token_usage(raw)
            
            return parsed, usage
            
        except Exception as e:
            logger.error(f"Error in detect_fake_reviews: {e}")
            return AuthenticityCheck(
                authenticity_score=50,
                flags=["Error during check"],
                reasoning="Analysis failed"
            ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def analyze_reviews(state: AgentState) -> AgentState:
    """Analyze reviews for sentiment and authenticity.
    
    Falls back to rating-based analysis if review text is unavailable.
    
    Args:
        state: Current agent state with reviews_data or products
        
    Returns:
        Updated state with review analysis
    """
    logger.info("=== Review Agent Starting ===")
    
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create review analysis step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.ANALYSIS,
            agent_name="review_agent"
        )
    
    try:
        agent = ReviewAgent()
        
        # Get reviews data from state
        reviews_data = state.get("reviews_data", {})
        products = state.get("products", [])
        
        # If no review text data, use rating-based analysis
        if not reviews_data:
            logger.info("No review text available, using rating-based analysis")
            analyzed_reviews = {}
            
            for product in products:
                asin = product.get("asin")
                if not asin:
                    continue
                    
                rating = product.get("rating")
                reviews_count = product.get("reviews_count") or product.get("reviews")
                
                # Skip if no rating data
                if rating is None:
                    continue
                
                # Generate analysis based on rating
                analyzed_reviews[asin] = analyze_from_rating(
                    product_title=product.get("title", "Unknown Product"),
                    rating=rating,
                    reviews_count=reviews_count or 0
                )
            
            if not analyzed_reviews:
                return {"review_analysis": {"error": "No rating data available for analysis"}}
                
            return {"review_analysis": analyzed_reviews}
            
        # Original review text analysis
        analyzed_reviews = {}
        total_tokens = {"input_tokens": 0, "output_tokens": 0}
        
        for asin, data in reviews_data.items():
            reviews = data.get("reviews", [])
            if not reviews:
                continue
                
            # Find product title
            product = next((p for p in products if p["asin"] == asin), {})
            product_title = product.get("title", "Unknown Product")
            
            # Run LLM analysis
            sentiment_analysis, sent_usage = agent.analyze_reviews_cot(product_title, reviews)
            authenticity_check, auth_usage = agent.detect_fake_reviews(product_title, reviews)
            
            # Accumulate tokens
            total_tokens["input_tokens"] += sent_usage.get("input_tokens", 0) + auth_usage.get("input_tokens", 0)
            total_tokens["output_tokens"] += sent_usage.get("output_tokens", 0) + auth_usage.get("output_tokens", 0)
            
            analyzed_reviews[asin] = {
                "summary": sentiment_analysis.summary,
                "sentiment_score": sentiment_analysis.sentiment_score,
                "authenticity_score": authenticity_check.authenticity_score,
                "pros": sentiment_analysis.pros,
                "cons": sentiment_analysis.cons,
                "flags": authenticity_check.flags,
                "aspect_sentiment": sentiment_analysis.aspect_sentiment
            }
        
        # Complete step with token usage
        if trace_id and step:
            total = total_tokens["input_tokens"] + total_tokens["output_tokens"]
            logger.info(f"Review Agent total tokens: {total_tokens['input_tokens']} input + {total_tokens['output_tokens']} output = {total} total")
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={"products_analyzed": len(analyzed_reviews)},
                token_usage=TokenUsage(
                    prompt_tokens=total_tokens["input_tokens"],
                    completion_tokens=total_tokens["output_tokens"],
                    total_tokens=total
                )
            )
            
    except Exception as e:
        logger.error(f"Error in Review Agent: {e}", exc_info=True)
        if trace_id and step:
            trace_manager.fail_step(trace_id, step.step_id, str(e))
    
    return {"review_analysis": analyzed_reviews}


def analyze_from_rating(product_title: str, rating: float, reviews_count: int) -> Dict[str, Any]:
    """Analyze product based on rating and review count.
    
    Args:
        product_title: Product name
        rating: Product rating (0-5)
        reviews_count: Number of reviews
        
    Returns:
        Analysis dict with sentiment and authenticity scores
    """
    # Sentiment score based on rating (normalize to 0-1)
    sentiment_score = rating / 5.0
    
    # Determine trustworthiness based on rating + review count
    if reviews_count >= 10000:
        volume_tier = "very high"
    elif reviews_count >= 1000:
        volume_tier = "high"
    elif reviews_count >= 100:
        volume_tier = "moderate"
    elif reviews_count >= 10:
        volume_tier = "low"
    else:
        volume_tier = "very low"
    
    # Generate summary
    if rating >= 4.5:
        rating_desc = "excellent"
    elif rating >= 4.0:
        rating_desc = "good"
    elif rating >= 3.5:
        rating_desc = "average"
    elif rating >= 3.0:
        rating_desc = "below average"
    else:
        rating_desc = "poor"
    
    summary = f"{rating_desc.capitalize()} rating of {rating}/5 based on {reviews_count:,} reviews ({volume_tier} validation volume)"
    
    # Generate pros based on high rating
    pros = []
    if rating >= 4.5:
        pros = [
            "High customer satisfaction",
            f"Strong rating of {rating}/5",
            "Positive overall feedback"
        ]
    elif rating >= 4.0:
        pros = [
            "Generally positive reviews",
            f"Good rating of {rating}/5"
        ]
    
    # Generate cons based on rating or low review count
    cons = []
    if rating < 4.0:
        cons.append(f"Below-average rating of {rating}/5")
    if reviews_count < 100:
        cons.append(f"Limited review validation ({reviews_count} reviews)")
    if rating < 3.5:
        cons.append("Significant customer concerns indicated")
    
    # Authenticity score based on review volume
    # High volume = more trustworthy, but also check for suspicious perfect ratings
    if reviews_count >= 1000:
        if rating >= 4.9:
            # Suspiciously high rating with many reviews
            authenticity_score = 75.0
            flags = ["Very high rating may indicate review manipulation"]
        else:
            authenticity_score = 90.0
            flags = []
    elif reviews_count >= 100:
        authenticity_score = 80.0
        flags = []
    elif reviews_count >= 10:
        authenticity_score = 70.0
        flags = ["Limited review sample"]
    else:
        authenticity_score = 50.0
        flags = ["Very limited review sample", "Insufficient data for validation"]
    
    return {
        "summary": summary,
        "sentiment_score": sentiment_score,
        "authenticity_score": authenticity_score,
        "pros": pros,
        "cons": cons if cons else ["No significant concerns"],
        "flags": flags,
        "aspect_sentiment": {
            "overall": rating_desc,
            "reliability": volume_tier
        },
        "analysis_method": "rating-based (no review text available)"
    }
