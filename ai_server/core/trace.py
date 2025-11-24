"""Real-time execution trace and monitoring system.

This module provides LangSmith-like monitoring capabilities:
- Agent execution traces
- Step-by-step outputs
- Token usage tracking
- Latency measurements
- Agent architecture visualization
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class StepType(str, Enum):
    """Types of execution steps."""
    ROUTER = "router"
    PLANNING = "planning"
    COLLECTION = "collection"
    ANALYSIS = "analysis"
    RESPONSE = "response"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"


class StepStatus(str, Enum):
    """Status of execution steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TokenUsage:
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionStep:
    """Single step in agent execution."""
    step_id: str
    step_type: StepType
    agent_name: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # Input/Output
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Metrics
    token_usage: Optional[TokenUsage] = None
    latency_ms: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_step_id: Optional[str] = None
    child_steps: List[str] = field(default_factory=list)
    
    def start(self) -> None:
        """Mark step as started."""
        self.status = StepStatus.RUNNING
        self.start_time = time.time()
    
    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000
        if output_data:
            self.output_data = output_data
    
    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.end_time = time.time()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "token_usage": self.token_usage.to_dict() if self.token_usage else None,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "parent_step_id": self.parent_step_id,
            "child_steps": self.child_steps,
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace for a query."""
    trace_id: str
    user_query: str
    session_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    total_duration_ms: Optional[float] = None
    
    # Steps
    steps: List[ExecutionStep] = field(default_factory=list)
    current_step: Optional[str] = None
    
    # Aggregated metrics
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    
    # Results
    success: bool = False
    error: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self) -> None:
        """Mark trace as started."""
        self.start_time = time.time()
    
    def complete(self, final_output: Optional[Dict[str, Any]] = None) -> None:
        """Mark trace as completed."""
        self.end_time = time.time()
        if self.start_time:
            self.total_duration_ms = (self.end_time - self.start_time) * 1000
        self.success = True
        if final_output:
            self.final_output = final_output
        self._aggregate_metrics()
    
    def fail(self, error: str) -> None:
        """Mark trace as failed."""
        self.end_time = time.time()
        if self.start_time:
            self.total_duration_ms = (self.end_time - self.start_time) * 1000
        self.success = False
        self.error = error
        self._aggregate_metrics()
    
    def add_step(self, step: ExecutionStep) -> None:
        """Add a step to the trace."""
        self.steps.append(step)
        self.current_step = step.step_id
    
    def _aggregate_metrics(self) -> None:
        """Aggregate metrics from all steps."""
        for step in self.steps:
            if step.token_usage:
                self.total_tokens += step.token_usage.total_tokens
            if step.step_type == StepType.LLM_CALL:
                self.total_llm_calls += 1
            if step.step_type == StepType.TOOL_CALL:
                self.total_tool_calls += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "user_query": self.user_query,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step,
            "total_tokens": self.total_tokens,
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "success": self.success,
            "error": self.error,
            "final_output": self.final_output,
            "metadata": self.metadata,
        }


class TraceManager:
    """Manages execution traces."""
    
    def __init__(self):
        self._traces: Dict[str, ExecutionTrace] = {}
        self._active_traces: Dict[str, str] = {}  # session_id -> trace_id
    
    def create_trace(
        self, 
        user_query: str, 
        session_id: Optional[str] = None
    ) -> ExecutionTrace:
        """Create a new execution trace."""
        trace_id = str(uuid.uuid4())
        trace = ExecutionTrace(
            trace_id=trace_id,
            user_query=user_query,
            session_id=session_id,
        )
        trace.start()
        
        self._traces[trace_id] = trace
        if session_id:
            self._active_traces[session_id] = trace_id
        
        return trace
    
    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Get trace by ID."""
        return self._traces.get(trace_id)
    
    def get_active_trace(self, session_id: str) -> Optional[ExecutionTrace]:
        """Get active trace for a session."""
        trace_id = self._active_traces.get(session_id)
        if trace_id:
            return self._traces.get(trace_id)
        return None
    
    def list_traces(
        self, 
        limit: int = 50, 
        session_id: Optional[str] = None
    ) -> List[ExecutionTrace]:
        """List recent traces."""
        traces = list(self._traces.values())
        
        if session_id:
            traces = [t for t in traces if t.session_id == session_id]
        
        # Sort by start time (most recent first)
        traces.sort(key=lambda t: t.start_time or 0, reverse=True)
        
        return traces[:limit]
    
    def create_step(
        self,
        trace_id: str,
        step_type: StepType,
        agent_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        parent_step_id: Optional[str] = None,
    ) -> Optional[ExecutionStep]:
        """Create a new step in a trace."""
        trace = self.get_trace(trace_id)
        if not trace:
            return None
        
        step_id = str(uuid.uuid4())
        step = ExecutionStep(
            step_id=step_id,
            step_type=step_type,
            agent_name=agent_name,
            input_data=input_data,
            parent_step_id=parent_step_id,
        )
        step.start()
        
        trace.add_step(step)
        
        # Add to parent's child steps
        if parent_step_id:
            for s in trace.steps:
                if s.step_id == parent_step_id:
                    s.child_steps.append(step_id)
                    break
        
        return step
    
    def complete_step(
        self,
        trace_id: str,
        step_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        token_usage: Optional[TokenUsage] = None,
    ) -> bool:
        """Mark a step as completed."""
        trace = self.get_trace(trace_id)
        if not trace:
            return False
        
        for step in trace.steps:
            if step.step_id == step_id:
                step.complete(output_data)
                if token_usage:
                    step.token_usage = token_usage
                    step.latency_ms = step.duration_ms
                return True
        
        return False
    
    def fail_step(
        self,
        trace_id: str,
        step_id: str,
        error: str,
    ) -> bool:
        """Mark a step as failed."""
        trace = self.get_trace(trace_id)
        if not trace:
            return False
        
        for step in trace.steps:
            if step.step_id == step_id:
                step.fail(error)
                return True
        
        return False


# Global trace manager instance
_trace_manager = TraceManager()


def get_trace_manager() -> TraceManager:
    """Get global trace manager instance."""
    return _trace_manager
