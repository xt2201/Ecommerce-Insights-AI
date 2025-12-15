from __future__ import annotations

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.schemas.shared_workspace import SharedWorkspace
import json
import logging

logger = logging.getLogger(__name__)

class ReviewerAgent:
    """
    Reviewer Agent (The Critic).
    Validates candidates for quality and trust using LLM.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="reviewer")
        self.prompts = load_prompts_as_dict("reviewer_agent_prompts")
        self.parser = JsonOutputParser()

    def review(self, workspace: SharedWorkspace) -> SharedWorkspace:
        """
        Validate candidates and set status (approved/rejected).
        """
        candidates = workspace.candidates
        # Only review 'proposed' or 'reviewed' (if Advisor touched them) candidates
        # Actually, Advisor leaves them as 'proposed'.
        targets = [c for c in candidates if c.status == "proposed"]
        
        if not targets:
            logger.info("ReviewerAgent: No candidates to review.")
            return workspace
            
        logger.info(f"ReviewerAgent: Reviewing {len(targets)} candidates.")
        
        # Prepare data for LLM
        candidates_data = []
        for c in targets:
            candidates_data.append({
                "asin": c.asin,
                "title": c.title,
                "price": c.price,
                "rating": c.source_data.get("rating", "N/A"),
                "reviews": c.source_data.get("reviews_count", "N/A"),
                "source": c.source_data.get("source", "Unknown")
            })
            
        # Construct Prompt
        system_prompt = self.prompts["system_prompt"]
        user_prompt = self.prompts["review_candidates_prompt"].format(
            goal=workspace.goal,
            candidates_json=json.dumps(candidates_data, indent=2)
        )
        
        try:
            # Call LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            parsed = self.parser.parse(response.content)
            
            reviews = parsed.get("reviews", [])
            review_map = {r["asin"]: r for r in reviews}
            
            # Update Candidates
            for candidate in targets:
                if candidate.asin in review_map:
                    review = review_map[candidate.asin]
                    candidate.status = review.get("status", "reviewed")
                    candidate.quality_score = float(review.get("quality_score", 0.5))
                    note = review.get("note")
                    if note:
                        candidate.notes.append(f"[Reviewer]: {note}")
                else:
                    # Fallback if LLM missed one
                    # Use heuristic fallback
                    rating = candidate.source_data.get("rating")
                    if rating and rating < 3.5:
                        candidate.status = "rejected"
                        candidate.quality_score = 0.3
                        candidate.notes.append("[Reviewer]: Low rating (Heuristic Fallback).")
                    else:
                        candidate.status = "approved"
                        candidate.quality_score = 0.7
                        candidate.notes.append("[Reviewer]: Approved (Fallback).")
                        
            logger.info("ReviewerAgent: Review complete.")
            
        except Exception as e:
            logger.error(f"ReviewerAgent LLM failed: {e}")
            # Fallback to heuristic
            for c in targets:
                rating = c.source_data.get("rating")
                if rating and rating < 3.0:
                    c.status = "rejected"
                else:
                    c.status = "approved"
                c.notes.append("[Reviewer]: LLM failed, using heuristic.")
                
        return workspace
