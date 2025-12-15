"""Hierarchical Context Manager (Stateless)."""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from ai_server.memory.vector_memory import VectorMemory
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.memory_models import SessionState, ConversationTurn

logger = logging.getLogger(__name__)

class HierarchicalContextManager:
    """Manages context updates and retrieval using SessionState and VectorMemory."""
    
    def __init__(self):
        self.vector_memory = VectorMemory()
        self.llm = get_llm(agent_name="manager")
        self.max_recent_turns = 5
        
    def add_turn(self, session: SessionState, turn: ConversationTurn) -> None:
        """Add turn to vector memory and update summary if needed.
        
        Args:
            session: Current session state.
            turn: The new turn being added.
        """
        # 1. Add to Vector Memory
        text_content = f"User: {turn.user_query}\nAI: {turn.top_recommendation or 'No recommendation'}"
        self.vector_memory.add_turn(
            text=text_content,
            metadata={
                "session_id": session.session_id,
                "timestamp": turn.timestamp.isoformat()
            }
        )
        
        # 2. Update Summary if needed
        # We summarize if we have enough turns and haven't summarized recently
        # Simple logic: Summarize every N turns or if history is long
        history = session.conversation_history.turns
        if len(history) > self.max_recent_turns and len(history) % 2 == 0:
            self._update_summary(session)
            
    def _update_summary(self, session: SessionState) -> None:
        """Update the rolling summary in the session."""
        recent_turns = session.conversation_history.get_recent_turns(self.max_recent_turns)
        current_summary = session.context_summary
        
        # Format turns
        conversation_text = ""
        for t in recent_turns:
            conversation_text += f"User: {t.user_query}\nAI: {t.top_recommendation or 'Response'}\n"
            
        prompt = (
            f"Current Summary: {current_summary}\n\n"
            f"Recent Conversation:\n{conversation_text}\n\n"
            "Update the summary to include key information from the recent conversation. "
            "Keep it concise (max 3 sentences). Focus on user preferences and key decisions."
        )
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a helpful assistant that summarizes conversations."),
                HumanMessage(content=prompt)
            ])
            session.context_summary = response.content
            logger.info(f"Updated session summary: {session.context_summary[:50]}...")
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            
    def get_semantic_context(self, session_id: str, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant past turns from vector memory."""
        return self.vector_memory.search(
            query=query,
            k=3,
            filter_metadata={"session_id": session_id}
        )

# Global instance
_context_manager = HierarchicalContextManager()

def get_context_manager() -> HierarchicalContextManager:
    return _context_manager
