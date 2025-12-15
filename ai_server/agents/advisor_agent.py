from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.schemas.shared_workspace import SharedWorkspace
import json
import logging

logger = logging.getLogger(__name__)

class AdvisorAgent:
    """
    Advisor Agent (The Expert).
    Analyzes candidates for domain fit using LLM.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="advisor") # Use 'advisor' config if available, else default
        self.prompts = load_prompts_as_dict("advisor_agent_prompts")
        self.parser = JsonOutputParser()

    def analyze(self, workspace: SharedWorkspace) -> SharedWorkspace:
        """
        Annotate candidates with domain insights.
        """
        candidates = workspace.candidates
        # Only analyze 'proposed' candidates
        targets = [c for c in candidates if c.status == "proposed"]
        
        if not targets:
            logger.info("AdvisorAgent: No new candidates to analyze.")
            return workspace
            
        logger.info(f"AdvisorAgent: Analyzing {len(targets)} candidates.")
        
        # Prepare data for LLM
        candidates_data = []
        for c in targets:
            candidates_data.append({
                "asin": c.asin,
                "title": c.title,
                "price": c.price,
                "specs": c.source_data.get("snippet", "") or c.source_data.get("title", "") # Fallback to title if no specs
            })
            
        # Construct Prompt
        system_prompt = self.prompts["system_prompt"]
        user_prompt = self.prompts["analyze_candidates_prompt"].format(
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
            
            if not parsed or not isinstance(parsed, dict):
                logger.warning(f"AdvisorAgent: Invalid LLM output format: {parsed}")
                assessments = []
            else:
                assessments = parsed.get("assessments", [])
            assessment_map = {a["asin"]: a for a in assessments}
            
            # Update Candidates
            for candidate in targets:
                if candidate.asin in assessment_map:
                    assessment = assessment_map[candidate.asin]
                    candidate.domain_score = float(assessment.get("domain_score", 0.5))
                    note = assessment.get("note")
                    if note:
                        candidate.notes.append(f"[Advisor]: {note}")
                else:
                    # Fallback if LLM missed one
                    candidate.domain_score = 0.5
                    candidate.notes.append("[Advisor]: No specific analysis provided.")
                    
            logger.info("AdvisorAgent: Analysis complete.")
            
        except Exception as e:
            logger.error(f"AdvisorAgent LLM failed: {e}")
            # Fallback to heuristic if LLM fails
            for c in targets:
                c.domain_score = 0.5
                c.notes.append("[Advisor]: Analysis failed, using default score.")
                
        return workspace
