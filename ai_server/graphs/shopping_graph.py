"""
Shopping Graph - Agentic Architecture

LLM-powered conversational AI with:
- QueryUnderstandingAgent for context-aware intent detection
- LLMRouter for intelligent routing
- SessionMemory for rich multi-turn conversation context
"""
from __future__ import annotations

import logging
import operator
from typing import Dict, Any, Optional, List, Annotated, TypedDict
from functools import wraps

from langgraph.graph import StateGraph, END

from ai_server.schemas.session_memory import SessionMemory, SearchIntent, ShownProduct
from ai_server.agents.query_understanding_agent import QueryUnderstandingAgent, QueryUnderstanding
from ai_server.agents.llm_router import LLMRouter
from ai_server.agents.search_agent import SearchAgent
from ai_server.agents.advisor_agent import AdvisorAgent
from ai_server.agents.response_generator import ResponseGenerator
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


# Graph State with proper TypedDict
class GraphState(TypedDict, total=False):
    """State flowing through the graph."""
    user_message: str
    session_id: str
    memory: Optional[SessionMemory]
    understanding: Optional[QueryUnderstanding]
    route: str
    search_query: Optional[str]
    candidates: List[Any]
    shown_products: List[ShownProduct]
    final_response: str
    artifacts: Dict[str, Any]  # Contains final_report with content for API response
    error: Optional[str]


# Initialize agents
query_understanding_agent = QueryUnderstandingAgent()
router = LLMRouter()
searcher = SearchAgent()
advisor = AdvisorAgent()
response_gen = ResponseGenerator()


def safe_node(func):
    """Error boundary decorator for graph nodes."""
    @wraps(func)
    def wrapper(state: GraphState) -> Dict[str, Any]:
        try:
            return func(state)
        except Exception as e:
            logger.error(f"Node {func.__name__} failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "route": "synthesize"
            }
    return wrapper


@safe_node
def understand_node(state: GraphState) -> Dict[str, Any]:
    """
    First node: Understand user message with full context.
    Uses LLM for ALL intent detection (100% agentic - no fast paths).
    """
    user_message = state.get("user_message", "")
    memory: SessionMemory = state.get("memory")
    
    if not memory:
        memory = SessionMemory(session_id=state.get("session_id", "default"))
    
    logger.info(f"UnderstandNode: Processing '{user_message[:50]}...'")
    
    # LLM-powered understanding for ALL messages (no fast paths)
    
    # Get rich understanding from LLM
    understanding = query_understanding_agent.understand(user_message, memory)
    
    # Determine route
    route = router.route(understanding, memory)
    
    # Update memory with user message
    memory.add_user_message(user_message, intent_type=understanding.message_type)
    
    # Handle intent updates - AGENTIC: Initialize intent for ANY message with search context
    has_search_context = bool(
        understanding.merged_search_query_en or 
        understanding.extracted_info.get("category") or
        understanding.extracted_info.get("keywords")
    )
    
    if router.is_new_search(understanding):
        # AGENTIC: Use LLM-determined is_refinement_only instead of hardcoded patterns
        # The LLM analyzes if message contains only constraints (gender, color, price)
        # without a new product category - this is fully agentic, no hardcoded patterns
        extracted = understanding.extracted_info or {}
        has_new_category = bool(extracted.get("category"))
        
        # LLM sets is_refinement_only=True when message only has constraints
        is_likely_refinement = (
            understanding.is_refinement_only and  # LLM-determined
            not has_new_category and
            memory.current_intent and 
            memory.current_intent.is_active
        )
        
        if is_likely_refinement:
            # LLM identified this as refinement - preserve intent
            logger.info(f"UnderstandNode: LLM detected refinement-only message (is_refinement_only=True) - treating as refinement")
            memory.current_intent.add_refinement(user_message)
            memory.current_intent.merge_constraints(extracted)
            # Keep the existing keywords, just add new ones
            if understanding.merged_search_query_en:
                existing_keywords = set(memory.current_intent.keywords_en or [])
                new_keywords = understanding.merged_search_query_en.split()[:5]
                memory.current_intent.keywords_en = list(existing_keywords.union(new_keywords))[:10]
        else:
            # Start fresh intent
            category = extracted.get("category")
            memory.start_new_intent(user_message, category)
            if memory.current_intent and extracted:
                memory.current_intent.merge_constraints(extracted)
                memory.current_intent.keywords_en = (
                    understanding.merged_search_query_en.split()[:5]
                    if understanding.merged_search_query_en else []
                )
    elif router.should_update_intent(understanding):
        # Refine existing intent - BUT create one if it doesn't exist
        if memory.current_intent:
            memory.current_intent.add_refinement(user_message)
            memory.current_intent.merge_constraints(understanding.extracted_info)
            if understanding.merged_search_query_en:
                memory.current_intent.keywords_en = understanding.merged_search_query_en.split()[:5]
        else:
            # AGENTIC FIX: Intent doesn't exist but we have a refinement - create intent!
            # This handles flows like: clarification→refinement (e.g., "shoes"→"sneaker")
            category = understanding.extracted_info.get("category")
            memory.start_new_intent(user_message, category)
            if memory.current_intent:
                memory.current_intent.merge_constraints(understanding.extracted_info)
                memory.current_intent.keywords_en = (
                    understanding.merged_search_query_en.split()[:5]
                    if understanding.merged_search_query_en else []
                )
                logger.info(f"UnderstandNode: Created intent from refine_search (no prior intent existed)")
    elif has_search_context and not memory.current_intent:
        # AGENTIC: If message has search context but no intent exists, create one
        # This handles consultation/clarification flows that build up search intent
        category = understanding.extracted_info.get("category")
        memory.start_new_intent(user_message, category)
        if memory.current_intent and understanding.extracted_info:
            memory.current_intent.merge_constraints(understanding.extracted_info)
            memory.current_intent.keywords_en = (
                understanding.merged_search_query_en.split()[:5]
                if understanding.merged_search_query_en else []
            )
        logger.info(f"UnderstandNode: Created intent from context-bearing message (type={understanding.message_type})")
    
    logger.info(f"UnderstandNode: route={route}, type={understanding.message_type}")
    
    return {
        "understanding": understanding,
        "memory": memory,
        "route": route,
        "search_query": understanding.merged_search_query_en
    }


def route_decision(state: GraphState) -> str:
    """Conditional routing based on understanding."""
    route = state.get("route", "clarification")
    logger.info(f"RouteDecision: {route}")
    return route


@safe_node
def greeting_node(state: GraphState) -> Dict[str, Any]:
    """Handle greetings - uses LLM for natural responses (100% agentic)."""
    user_message = state.get("user_message", "")
    memory: SessionMemory = state.get("memory")
    
    # Use LLM to generate greeting response
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_server.llm.llm_factory import get_llm
    from ai_server.utils.prompt_loader import load_prompts_as_dict
    
    llm = get_llm(agent_name="manager")
    
    try:
        prompts = load_prompts_as_dict("graph_node_prompts")
        greeting_prompts = prompts.get("greeting", {})
        system_prompt = greeting_prompts.get("system_prompt", 
            "Generate a friendly greeting as a shopping assistant. Ask what they're looking for.")
    except Exception:
        system_prompt = "Generate a friendly greeting as a shopping assistant."
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=greeting_prompts.get("user_prompt_template", "User: {user_message}").format(user_message=user_message))
        ]
        response = llm.invoke(messages)
        greeting = response.content.strip()
        
        if "<think>" in greeting:
            greeting = greeting.split("</think>")[-1].strip()
    except Exception as e:
        logger.error(f"GreetingNode: LLM failed: {e}")
        greeting = "Hello! I'm your AI Shopping Assistant. How can I help you today?"
    
    if memory:
        memory.add_assistant_message(greeting)
    
    logger.info("GreetingNode: Generated greeting (agentic)")
    
    # Build artifacts for consistent API response
    artifacts = {
        "final_report": {
            "type": "greeting_response",
            "content": greeting,
            "summary": greeting[:200] if greeting else "Greeting",
            "follow_up_suggestions": [
                "I'm looking for electronics",
                "Help me find a gift",
                "Show me today's deals"
            ]
        }
    }
    
    return {
        "final_response": greeting,
        "memory": memory,
        "artifacts": artifacts,
        "route": "end"
    }


@safe_node
def search_node(state: GraphState) -> Dict[str, Any]:
    """Execute search using merged query from understanding OR memory's accumulated context."""
    understanding: QueryUnderstanding = state.get("understanding")
    memory: SessionMemory = state.get("memory")
    
    # Primary: use understanding's merged query
    search_query = understanding.merged_search_query_en or state.get("search_query", "")
    
    # Fallback: use memory's accumulated intent (for confirmation messages)
    if not search_query and memory and memory.current_intent:
        intent = memory.current_intent
        # Build query from accumulated constraints
        keywords = intent.get_merged_keywords()
        category = intent.category or ""
        
        if keywords or category:
            search_query = f"{category} {keywords}".strip()
            logger.info(f"SearchNode: Using accumulated query from memory: '{search_query}'")
    
    if not search_query:
        logger.warning("SearchNode: No search query provided")
        return {
            "route": "clarification",
            "memory": memory
        }
    
    logger.info(f"SearchNode: Searching for '{search_query}'")
    
    # Create workspace for SearchAgent (bridge to existing code)
    from ai_server.schemas.shared_workspace import SharedWorkspace, DevelopmentPlan
    from ai_server.schemas.conversation_context import ConversationContext
    
    workspace = SharedWorkspace(
        goal=search_query,
        search_query=search_query,
        user_message=state.get("user_message", ""),
        plan=DevelopmentPlan(goal=search_query, steps=[]),
        conversation=ConversationContext()
    )
    
    # Execute search
    result = searcher.search(workspace)
    
    # Convert candidates to ShownProducts and store in memory
    shown_products = []
    for c in result.candidates[:10]:
        product = ShownProduct(
            asin=c.asin,
            title=c.title,
            price=c.price,
            image_url=c.source_data.get("image") if c.source_data else None,
            rating=c.source_data.get("rating") if c.source_data else None
        )
        shown_products.append(product)
    
    if memory:
        memory.add_shown_products(shown_products)
    
    logger.info(f"SearchNode: Found {len(shown_products)} products")
    
    return {
        "candidates": result.candidates,
        "shown_products": shown_products,
        "memory": memory,
        "route": "analyze"
    }


@safe_node
def analyze_node(state: GraphState) -> Dict[str, Any]:
    """Analyze and rank candidates."""
    candidates = state.get("candidates", [])
    memory: SessionMemory = state.get("memory")
    
    if not candidates:
        return {
            "route": "synthesize",
            "memory": memory
        }
    
    # Use advisor to enrich candidates
    from ai_server.schemas.shared_workspace import SharedWorkspace, DevelopmentPlan
    from ai_server.schemas.conversation_context import ConversationContext
    
    workspace = SharedWorkspace(
        goal=state.get("search_query", ""),
        candidates=candidates,
        plan=DevelopmentPlan(goal="analyze", steps=[]),
        conversation=ConversationContext()
    )
    
    result = advisor.analyze(workspace)
    
    return {
        "candidates": result.candidates,
        "memory": memory,
        "route": "synthesize"
    }


@safe_node
def consultation_node(state: GraphState) -> Dict[str, Any]:
    """Consultation about shown products - uses external prompts (100% agentic)."""
    understanding: QueryUnderstanding = state.get("understanding")
    memory: SessionMemory = state.get("memory")
    
    if not memory or not memory.shown_products:
        logger.warning("ConsultationNode: No products to discuss")
        return {
            "final_response": "I couldn't find any products to discuss. What would you like to search for?",
            "route": "end",
            "memory": memory
        }
    
    # Build products context
    products_info = []
    for i, p in enumerate(memory.shown_products[:10], 1):
        price_str = f"${p.price}" if p.price else "N/A"
        rating_str = f"{p.rating}★" if p.rating else ""
        products_info.append(f"{i}. {p.title} - {price_str} {rating_str}")
    
    products_context = "\n".join(products_info)
    
    # Generate consultation response using external prompts
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_server.llm.llm_factory import get_llm
    from ai_server.utils.prompt_loader import load_prompts_as_dict
    
    llm = get_llm(agent_name="manager")
    
    consultation_type = understanding.consultation_type or "general"
    question = understanding.consultation_question or state.get("user_message", "")
    
    # Load prompts from external file
    try:
        prompts = load_prompts_as_dict("consultation_prompts")
        system_prompt = prompts.get("system_prompt", "You are an AI Shopping Assistant.")
        user_template = prompts.get("user_prompt_template", "{products_context}\n{question}")
    except Exception as e:
        logger.warning(f"ConsultationNode: Failed to load prompts: {e}")
        system_prompt = "You are an AI Shopping Assistant. Help the customer compare products."
        user_template = "Products:\n{products_context}\n\nQuestion: {question}"
    
    user_prompt = user_template.format(
        products_context=products_context,
        question=question,
        consultation_type=consultation_type
    )
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        consultation_response = response.content
        
        # Clean think blocks
        if "<think>" in consultation_response:
            consultation_response = consultation_response.split("</think>")[-1].strip()
        
    except Exception as e:
        logger.error(f"ConsultationNode: LLM failed: {e}")
        consultation_response = "Sorry, I couldn't provide consultation at this time."
    
    if memory:
        memory.add_assistant_message(consultation_response)
    
    logger.info("ConsultationNode: Generated consultation response")
    
    # Build artifacts for consistent API response
    artifacts = {
        "final_report": {
            "type": "consultation_response",
            "content": consultation_response,
            "summary": consultation_response[:200] if consultation_response else "Consultation",
            "follow_up_suggestions": [
                "Show me more options",
                "Compare these products",
                "Search for something else"
            ]
        }
    }
    
    return {
        "final_response": consultation_response,
        "memory": memory,
        "artifacts": artifacts,
        "route": "end"
    }


@safe_node
def pre_search_consultation_node(state: GraphState) -> Dict[str, Any]:
    """
    Pre-search consultation node - provides expert advice before searching.
    
    This node is triggered when we have some information but not enough
    to execute a search confidently. It provides consultation advice
    and may ask final clarifying questions.
    """
    memory: SessionMemory = state.get("memory")
    understanding: QueryUnderstanding = state.get("understanding")
    user_message = state.get("user_message", "")
    
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_server.llm.llm_factory import get_llm
    from ai_server.utils.prompt_loader import load_prompts_as_dict
    
    llm = get_llm(agent_name="manager")
    
    # Build context for consultation
    original_query = ""
    category = "unknown"
    known_constraints = []
    
    if memory and memory.current_intent:
        original_query = memory.current_intent.original_query or user_message
        category = memory.current_intent.category or "unknown"
        for key, value in memory.current_intent.constraints.items():
            if value:
                known_constraints.append(f"- {key}: {value}")
    else:
        original_query = user_message
    
    # Get conversation context
    conversation_context = ""
    if memory and memory.turns:
        recent = memory.get_recent_turns(4)
        conversation_context = "\n".join(
            f"{t.role.title()}: {t.content[:80]}..." if len(t.content) > 80 else f"{t.role.title()}: {t.content}"
            for t in recent
        )
    
    # Load prompts
    try:
        prompts = load_prompts_as_dict("pre_search_consultation_prompts")
        system_prompt = prompts.get("system_prompt", "")
        user_template = prompts.get("user_prompt_template", "")
    except Exception as e:
        logger.warning(f"PreSearchConsultationNode: Failed to load prompts: {e}")
        system_prompt = """You are an AI Shopping Consultant. The customer is shopping but needs advice before searching.
        Acknowledge their needs, provide helpful suggestions, and ask if they're ready to search."""
        user_template = "Original request: {original_query}\nKnown info: {known_constraints}\nProvide helpful consultation."
    
    # Build user prompt
    user_prompt = user_template.format(
        original_query=original_query,
        category=category,
        known_constraints="\n".join(known_constraints) if known_constraints else "None gathered yet",
        missing_info="(to be determined by LLM)",
        conversation_context=conversation_context or "New conversation"
    )
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        consultation_response = response.content.strip()
        
        # Clean think blocks
        if "<think>" in consultation_response:
            consultation_response = consultation_response.split("</think>")[-1].strip()
        
    except Exception as e:
        logger.error(f"PreSearchConsultationNode: LLM failed: {e}")
        consultation_response = (
            f"I understand you're looking for {category or 'products'}. "
            "Before I search, could you tell me a bit more about your preferences? "
            "Or if you're ready, just say 'search' and I'll find options for you!"
        )
    
    if memory:
        memory.add_assistant_message(consultation_response)
    
    logger.info("PreSearchConsultationNode: Generated consultation response (agentic)")
    
    # Build artifacts for consistent API response
    artifacts = {
        "final_report": {
            "type": "pre_search_consultation_response",
            "content": consultation_response,
            "summary": consultation_response[:200] if consultation_response else "Pre-search consultation",
            "follow_up_suggestions": [
                "Ok, search now",
                "Let me add more details",
                "Show me popular options first"
            ]
        }
    }
    
    return {
        "final_response": consultation_response,
        "memory": memory,
        "artifacts": artifacts,
        "route": "end"
    }


@safe_node
def faq_node(state: GraphState) -> Dict[str, Any]:
    """
    Handle FAQ/Policy questions using RAG from KnowledgeBase + KnowledgeGraph.
    
    Uses:
    - KnowledgeBase for semantic search on policies/FAQs
    - KnowledgeGraph for entity relationships and enhanced context
    - LLM for generating natural language answers
    
    Supports bilingual (EN/VI) with automatic language detection.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_server.llm.llm_factory import get_llm
    from ai_server.utils.prompt_loader import load_prompts_as_dict
    from ai_server.rag.knowledge_base import get_knowledge_base
    from ai_server.rag.knowledge_graph import get_knowledge_graph
    
    memory: SessionMemory = state.get("memory")
    understanding: QueryUnderstanding = state.get("understanding")
    user_message = state.get("user_message", "")
    
    logger.info(f"FAQNode: Processing FAQ query '{user_message[:50]}...'")
    
    # Initialize RAG components
    kb = get_knowledge_base()
    kg = get_knowledge_graph()
    
    # Detect language
    detected_language = kb.detect_language(user_message)
    language_instruction = "Vietnamese" if detected_language == "vi" else "English"
    
    # Retrieve context from KnowledgeBase (policies/FAQs)
    kb_context = kb.query(
        query_text=user_message,
        k=5,
        language=detected_language,
    )
    
    # Retrieve context from KnowledgeGraph (entity relationships)
    kg_context = kg.get_entity_context(
        query=user_message,
        language=detected_language,
        max_entities=5,
    )
    
    # Load FAQ prompts
    try:
        prompts = load_prompts_as_dict("faq_prompts")
    except Exception as e:
        logger.warning(f"Failed to load FAQ prompts: {e}")
        prompts = {}
    
    # Select system prompt based on language
    if detected_language == "vi":
        system_prompt = prompts.get("system_prompt_vi", prompts.get("system_prompt", ""))
    else:
        system_prompt = prompts.get("system_prompt", "")
    
    # Check if we have context
    if not kb_context and not kg_context:
        # No relevant context found
        if detected_language == "vi":
            response = prompts.get("no_context_response_vi", 
                "Xin lỗi, tôi không có thông tin về vấn đề đó. Bạn có thể hỏi về chính sách đổi trả, vận chuyển, thanh toán, bảo hành hoặc tài khoản.")
        else:
            response = prompts.get("no_context_response",
                "I apologize, but I don't have specific information about that. You can ask about return policies, shipping, payments, warranty, or account management.")
        
        if memory:
            memory.add_assistant_message(response)
        
        artifacts = {
            "final_report": {
                "type": "faq_response",
                "content": response,
                "summary": "No relevant policy information found",
                "language": detected_language,
                "kb_context": "",
                "kg_context": "",
                "follow_up_suggestions": []
            }
        }
        
        return {
            "final_response": response,
            "memory": memory,
            "artifacts": artifacts,
            "detected_language": detected_language,
            "kb_context": "",
            "kg_context": "",
            "route": "end"
        }
    
    # Build user prompt
    if detected_language == "vi":
         user_prompt_template = prompts.get("user_prompt_template_vi") or prompts.get("user_prompt_template")
    else:
         user_prompt_template = prompts.get("user_prompt_template")
         
    user_prompt_template = user_prompt_template or """## Relevant Policy & FAQ Context
{context}

## Knowledge Graph Context (Related Policies)
{kg_context}

## Customer Question
{question}

## Customer Language
{language}

Provide a helpful, accurate answer based on the context above.
Respond in {language_instruction}."""
    
    user_prompt = user_prompt_template.format(
        context=kb_context or "No specific policy context available.",
        kg_context=kg_context or "No additional relationships found.",
        question=user_message,
        language=detected_language,
        language_instruction=language_instruction,
    )
    
    # Generate response using LLM
    try:
        llm = get_llm(agent_name="manager")
        messages = [
            SystemMessage(content=system_prompt or "You are a helpful customer service assistant."),
            HumanMessage(content=user_prompt),
        ]
        
        llm_response = llm.invoke(messages)
        response = llm_response.content
        
        # Clean response if needed
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()
        
    except Exception as e:
        logger.error(f"FAQNode: LLM generation failed: {e}")
        # Fallback to returning context directly
        response = kb_context if kb_context else "I'm sorry, I couldn't generate a response. Please try again."
    
    # Update memory
    if memory:
        memory.add_assistant_message(response)
    
    # Generate follow-up suggestions based on category
    follow_up_suggestions = []
    if detected_language == "vi":
        follow_up_suggestions = [
            "Thời gian giao hàng là bao lâu?",
            "Làm thế nào để đổi trả sản phẩm?",
            "Các phương thức thanh toán được chấp nhận?"
        ]
    else:
        follow_up_suggestions = [
            "How long does shipping take?",
            "How do I return an item?",
            "What payment methods do you accept?"
        ]
    
    logger.info(f"FAQNode: Generated response ({len(response)} chars) in {detected_language}")
    
    # Build artifacts
    artifacts = {
        "final_report": {
            "type": "faq_response",
            "content": response,
            "summary": response[:200] if len(response) > 200 else response,
            "language": detected_language,
            "kb_context": kb_context[:500] if kb_context else "",
            "kg_context": kg_context[:500] if kg_context else "",
            "follow_up_suggestions": follow_up_suggestions
        }
    }
    
    return {
        "final_response": response,
        "memory": memory,
        "artifacts": artifacts,
        "detected_language": detected_language,
        "kb_context": kb_context,
        "kg_context": kg_context,
        "route": "end"
    }


@safe_node
def clarification_node(state: GraphState) -> Dict[str, Any]:
    """Ask for clarification - uses LLM to generate context-aware questions (100% agentic)."""
    memory: SessionMemory = state.get("memory")
    understanding: QueryUnderstanding = state.get("understanding")
    user_message = state.get("user_message", "")
    
    # Use LLM-powered ClarificationAgent
    from ai_server.agents.clarification_agent import get_clarification_agent
    
    clarification_agent = get_clarification_agent()
    result = clarification_agent.generate_questions(memory, user_message)
    
    # Build response from LLM-generated questions
    if result.questions:
        response = "\n".join(f"- {q}" for q in result.questions)
    else:
        # Fallback if LLM returned no questions
        response = "What type of product are you looking for?"
    
    if memory:
        memory.add_assistant_message(response)
    
    logger.info(f"ClarificationNode: Generated {len(result.questions)} questions (agentic)")
    
    # Build artifacts for consistent API response
    artifacts = {
        "final_report": {
            "type": "clarification_response",
            "content": response,
            "summary": response[:200] if response else "Clarification",
            "follow_up_suggestions": result.questions[:3] if result.questions else []
        }
    }
    
    return {
        "final_response": response,
        "memory": memory,
        "artifacts": artifacts,
        "route": "end"
    }


@safe_node
def synthesize_node(state: GraphState) -> Dict[str, Any]:
    """Generate final response with product recommendations - uses LLM (100% agentic)."""
    candidates = state.get("candidates", [])
    memory: SessionMemory = state.get("memory")
    understanding: QueryUnderstanding = state.get("understanding")
    search_query = state.get("search_query", "")
    
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_server.llm.llm_factory import get_llm
    from ai_server.utils.prompt_loader import load_prompts_as_dict
    
    llm = get_llm(agent_name="manager")
    
    # Load prompts
    try:
        prompts = load_prompts_as_dict("synthesis_prompts")
    except Exception:
        prompts = {}
    
    if not candidates:
        # No results case
        original_user_message = state.get("user_message", search_query)
        
        no_results_prompt = prompts.get("no_results_response",
            "No products found. Suggest alternatives or ask what else they're looking for.")
        
        # Format if placeholders exist
        formatted_prompt = no_results_prompt.replace("{query}", search_query).replace("{original_query}", original_user_message)
        
        try:
            messages = [
                SystemMessage(content=formatted_prompt),
                # HumanMessage is redundant if prompt is comprehensive, but keeping consistent structure
                HumanMessage(content=f"Generate 'no results' response for: {original_user_message}")
            ]
            resp = llm.invoke(messages)
            response = resp.content.strip()
            if "<think>" in response:
                response = response.split("</think>")[-1].strip()
        except Exception:
            response = "Sorry, I couldn't find matching products. Would you like to try a different search?"
    else:
        # Get original user message for language detection
        original_user_message = state.get("user_message", search_query)
        
        # Build products list with more details
        products_list = []
        for i, c in enumerate(candidates[:5], 1):
            price_str = f"${c.price}" if c.price else "N/A"
            rating_str = f", Rating: {c.source_data.get('rating', 'N/A')}" if c.source_data else ""
            specs = c.source_data.get("snippet", "")[:100] if c.source_data else ""
            products_list.append(f"{i}. {c.title} - {price_str}{rating_str}")
            if specs:
                products_list.append(f"   Specs: {specs}")
        
        # Build advisor analysis text from candidate notes and domain scores
        advisor_analysis_lines = []
        for i, c in enumerate(candidates[:5], 1):
            notes = " | ".join(c.notes) if c.notes else "No specific analysis"
            domain_score = getattr(c, 'domain_score', 0.5)
            advisor_analysis_lines.append(
                f"{i}. {c.title[:50]}...: Fit Score={domain_score:.1f}/1.0, Analysis: {notes}"
            )
        advisor_analysis = "\n".join(advisor_analysis_lines) if advisor_analysis_lines else "No expert analysis available"
        
        system_prompt = prompts.get("system_prompt",
            "Present these products to the customer in a helpful, conversational way.")
        user_template = prompts.get("user_prompt_template",
            "Search: {search_query}\n\nProducts:\n{products_list}")
        
        # Format with all required fields
        try:
            user_prompt = user_template.format(
                original_user_message=original_user_message,
                search_query=search_query,
                products_list="\n".join(products_list),
                advisor_analysis=advisor_analysis
            )
        except KeyError:
            # Fallback for old template format
            user_prompt = f"Customer asked: {original_user_message}\n\nProducts:\n" + "\n".join(products_list)
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            resp = llm.invoke(messages)
            response = resp.content.strip()
            if "<think>" in response:
                response = response.split("</think>")[-1].strip()
        except Exception as e:
            logger.error(f"SynthesizeNode: LLM failed: {e}")
            # Fallback: simple list
            response = "Here are the products I found:\n" + "\n".join(products_list)
    
    if memory:
        memory.add_assistant_message(response)
    
    logger.info("SynthesizeNode: Generated response (agentic)")
    
    # Build artifacts structure for server.py compatibility
    artifacts = {
        "final_report": {
            "type": "recommendation_report" if candidates else "no_results_report",
            "content": response,  # This becomes final_answer
            "summary": response[:200] if response else "No summary",
            "follow_up_suggestions": [
                "Would you like me to search for something else?",
                "Need more details on any of these products?"
            ] if candidates else [
                "Try a different search term",
                "Let me know what you're looking for"
            ]
        }
    }
    
    return {
        "final_response": response,
        "candidates": candidates,
        "memory": memory,
        "artifacts": artifacts,
        "route": "end"
    }


def build_graph():
    """Build the agentic shopping graph."""
    
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("understand", understand_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("search", search_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("consultation", consultation_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("pre_search_consultation", pre_search_consultation_node)  # Consultative flow
    workflow.add_node("faq", faq_node)  # FAQ/Policy RAG node
    workflow.add_node("synthesize", synthesize_node)
    
    # Entry point
    workflow.set_entry_point("understand")
    
    # Conditional routing from understand node
    workflow.add_conditional_edges(
        "understand",
        route_decision,
        {
            "greeting": "greeting",
            "search": "search",
            "consultation": "consultation",
            "clarification": "clarification",
            "pre_search_consultation": "pre_search_consultation",
            "faq": "faq",  # FAQ/Policy questions → RAG node
            "order_status": "clarification",  # TODO: Implement order node
            "confirmation": "search",  # User confirmation → proceed to search
            "synthesize": "synthesize"
        }
    )
    
    # Search -> Analyze -> Synthesize
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "synthesize")
    
    # Terminal nodes
    workflow.add_edge("greeting", END)
    workflow.add_edge("consultation", END)
    workflow.add_edge("clarification", END)
    workflow.add_edge("pre_search_consultation", END)
    workflow.add_edge("faq", END)  # FAQ responses are terminal
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()


# Export compiled graph
graph = build_graph()
