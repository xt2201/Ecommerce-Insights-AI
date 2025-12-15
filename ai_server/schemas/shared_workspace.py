from typing import List, Dict, Any, Literal, Optional, Annotated
import operator
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from ai_server.schemas.conversation_context import ConversationContext

def merge_candidates(existing: List['ProductCandidate'], new: List['ProductCandidate']) -> List['ProductCandidate']:
    """Custom reducer to merge candidate lists by ASIN."""
    if not existing:
        return new
    if not new:
        return existing
        
    # Map existing by ASIN
    existing_map = {c.asin: c for c in existing}
    
    for c in new:
        if c.asin in existing_map:
            # Merge fields
            existing_c = existing_map[c.asin]
            if c.domain_score is not None: existing_c.domain_score = c.domain_score
            if c.quality_score is not None: existing_c.quality_score = c.quality_score
            if c.status != "proposed": existing_c.status = c.status
            # Avoid duplicating notes if they are identical? 
            # For now just extend, assuming unique notes from agents
            if c.notes:
                existing_c.notes.extend([n for n in c.notes if n not in existing_c.notes])
        else:
            existing_map[c.asin] = c
            
    return list(existing_map.values())

class ProductCandidate(BaseModel):
    """A product candidate in the shared workspace."""
    asin: str
    title: str
    price: Optional[float] = None
    status: Literal["proposed", "reviewed", "rejected", "approved"] = "proposed"
    domain_score: Optional[float] = None  # Score from Advisor (0-1)
    quality_score: Optional[float] = None # Score from Reviewer (0-1)
    notes: List[str] = Field(default_factory=list) # Collaborative notes from agents
    source_data: Dict[str, Any] = Field(default_factory=dict) # Raw data from search

class DevelopmentPlan(BaseModel):
    """The dynamic plan managed by the Manager."""
    goal: str
    steps: List[str]
    current_step_index: int = 0
    status: Literal["planning", "executing", "completed", "failed"] = "planning"

class SharedWorkspace(BaseModel):
    """The shared state (Whiteboard) for all agents."""
    goal: str
    user_message: str = ""  # Raw user message (current turn)
    plan: DevelopmentPlan
    # Use Annotated with reducer for parallel merging
    candidates: Annotated[List[ProductCandidate], merge_candidates] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict) # Final deliverables
    messages: Annotated[List[BaseMessage], operator.add] = Field(default_factory=list) # Chat history
    
    # Conversation context for multi-turn dialogue
    conversation: ConversationContext = Field(default_factory=ConversationContext)
    
    # Metadata for graph control flow
    next_agent: Optional[str] = None
    next_tool: Optional[Dict[str, Any]] = None # {name: str, args: dict}
    search_query: Optional[str] = None # Override for search agent (e.g. refinement)
    error: Optional[str] = None
    
    # Circuit breaker fields
    loop_count: int = 0
    max_loops: int = 20
    search_attempts: int = 0
    max_search_attempts: int = 3


