"""Agent architecture information and visualization.

Provides detailed information about agent structure, similar to LangSmith's agent view.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentNode:
    """Represents a single agent in the graph."""
    name: str
    type: str  # router, planning, collection, analysis, response
    description: str
    
    # Configuration
    provider: str  # gemini, cerebras
    model: str
    temperature: float
    max_tokens: int
    
    # Connections
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    
    # Tools/Capabilities
    tools: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tools": self.tools,
            "prompts": self.prompts,
        }


@dataclass
class AgentEdge:
    """Represents a connection between agents."""
    source: str
    target: str
    condition: Optional[str] = None  # Conditional routing
    label: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
            "label": self.label,
        }


@dataclass
class AgentArchitecture:
    """Complete agent architecture."""
    name: str
    description: str
    version: str
    
    # Graph structure
    nodes: List[AgentNode] = field(default_factory=list)
    edges: List[AgentEdge] = field(default_factory=list)
    
    # Entry/Exit points
    entry_point: str = "router"
    exit_points: List[str] = field(default_factory=lambda: ["response"])
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "entry_point": self.entry_point,
            "exit_points": self.exit_points,
            "metadata": self.metadata,
        }


def get_agent_architecture() -> AgentArchitecture:
    """Get current agent architecture from config.
    
    Returns detailed information about all agents and their connections.
    """
    from ai_server.core.config import get_config_value
    
    # Create architecture
    arch = AgentArchitecture(
        name="Amazon Smart Shopping Assistant",
        description="Multi-agent system for intelligent Amazon product search and recommendations",
        version="2.0",
        metadata={
            "framework": "LangGraph",
            "language": "Python",
            "features": ["routing", "planning", "memory", "personalization"],
        }
    )
    
    # Router Agent
    router_node = AgentNode(
        name="router",
        type="router",
        description="Routes queries to appropriate workflow (quick search, clarification, or full search)",
        provider=get_config_value("agents.router.provider", "cerebras"),
        model=get_config_value("agents.router.model_name", "llama3.1-8b"),
        temperature=get_config_value("agents.router.temperature", 0.0),
        max_tokens=get_config_value("agents.router.max_tokens", 2000),
        outputs=["planning", "response"],
        tools=[],
        prompts=["router_agent_prompts.md"],
    )
    arch.nodes.append(router_node)
    
    # Planning Agent
    planning_node = AgentNode(
        name="planning",
        type="planning",
        description="Analyzes query intent and creates search plan with autonomous tool usage",
        provider=get_config_value("agents.planning.provider", "cerebras"),
        model=get_config_value("agents.planning.model_name", "qwen-3-32b"),
        temperature=get_config_value("agents.planning.temperature", 0.1),
        max_tokens=get_config_value("agents.planning.max_tokens", 4000),
        inputs=["router"],
        outputs=["collection"],
        tools=["analyze_query_intent", "expand_keywords", "extract_requirements"],
        prompts=["planning_agent_prompts.md"],
    )
    arch.nodes.append(planning_node)
    
    # Collection Agent
    collection_node = AgentNode(
        name="collection",
        type="collection",
        description="Gathers product data from SerpAPI based on search plan",
        provider="N/A",
        model="N/A",
        temperature=0.0,
        max_tokens=0,
        inputs=["planning"],
        outputs=["analysis"],
        tools=["serpapi_search"],
        prompts=[],
    )
    arch.nodes.append(collection_node)
    
    # Analysis Agent
    analysis_node = AgentNode(
        name="analysis",
        type="analysis",
        description="Chain-of-thought analysis of products with personalized scoring",
        provider=get_config_value("agents.analysis.provider", "cerebras"),
        model=get_config_value("agents.analysis.model_name", "qwen-3-32b"),
        temperature=get_config_value("agents.analysis.temperature", 0.2),
        max_tokens=get_config_value("agents.analysis.max_tokens", 8000),
        inputs=["collection"],
        outputs=["response"],
        tools=[],
        prompts=["analysis_agent_prompts.md"],
    )
    arch.nodes.append(analysis_node)
    
    # Response Agent
    response_node = AgentNode(
        name="response",
        type="response",
        description="Generates user-facing response with recommendations",
        provider=get_config_value("agents.response.provider", "cerebras"),
        model=get_config_value("agents.response.model_name", "qwen-3-32b"),
        temperature=get_config_value("agents.response.temperature", 0.3),
        max_tokens=get_config_value("agents.response.max_tokens", 8000),
        inputs=["router", "analysis"],
        outputs=[],
        tools=[],
        prompts=["response_agent_prompts.md"],
    )
    arch.nodes.append(response_node)
    
    # Define edges (connections)
    arch.edges = [
        AgentEdge(
            source="router",
            target="planning",
            condition="route == 'full_search'",
            label="Full Search"
        ),
        AgentEdge(
            source="router",
            target="response",
            condition="route in ['quick_search', 'clarification']",
            label="Quick/Clarification"
        ),
        AgentEdge(
            source="planning",
            target="collection",
            label="Search Plan"
        ),
        AgentEdge(
            source="collection",
            target="analysis",
            label="Products"
        ),
        AgentEdge(
            source="analysis",
            target="response",
            label="Analysis"
        ),
    ]
    
    return arch


def get_agent_statistics() -> Dict[str, Any]:
    """Get statistics about agent usage.
    
    Returns:
        Dictionary with agent statistics
    """
    from ai_server.core.config import load_config
    
    config = load_config()
    
    return {
        "total_agents": 5,
        "llm_providers": {
            "cerebras": ["router", "planning", "analysis", "response"],
            "gemini": [],  # Can be configured
        },
        "tools": {
            "planning": 3,
            "collection": 1,
            "analysis": 0,
        },
        "prompts": {
            "router": 1,
            "planning": 1,
            "analysis": 1,
            "response": 1,
        },
        "configuration": {
            "langsmith_enabled": config.langsmith.enabled if hasattr(config, 'langsmith') else False,
            "memory_enabled": True,
            "personalization_enabled": True,
        }
    }
