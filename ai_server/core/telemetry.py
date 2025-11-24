"""Telemetry helpers for optional LangSmith integration.

LangSmith API key is loaded from environment (.env)
Configuration settings from config.yaml
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

from ai_server.core.config import get_api_key, get_config_value

_LOGGER = logging.getLogger(__name__)

_DEFAULT_PROJECT_NAME = "Amazon Smart Shopping Assistant"
_TRACE_ATTR = "__langsmith_traced__"

_F = TypeVar("_F", bound=Callable[..., object])


def _load_langsmith_client():  # pragma: no cover - thin import wrapper
    try:
        from langsmith import Client  # type: ignore
    except ImportError:
        return None
    return Client


def configure_langsmith(
    *,
    project_name: Optional[str] = None,
    enable_tracing: bool = True,
) -> Optional["Client"]:
    """Configure LangSmith tracing using the API key from environment.

    Returns the instantiated :class:`langsmith.Client` when successful, or ``None``
    when LangSmith integration is disabled or unavailable.
    """
    
    # Check if LangSmith is enabled in config
    enabled = get_config_value("langsmith.enabled", True)
    if not enabled:
        _LOGGER.debug("LangSmith disabled in config")
        return None

    client_cls = _load_langsmith_client()
    if client_cls is None:  # pragma: no cover - defensive guard for optional dep
        _LOGGER.debug("LangSmith not installed; skipping telemetry setup")
        return None

    # Get API key from environment
    try:
        key = get_api_key("LANGSMITH_API_KEY")
    except Exception:
        _LOGGER.debug("LangSmith API key missing; telemetry disabled")
        return None

    # Get project name from config or parameter
    config_project = get_config_value("langsmith.project_name", _DEFAULT_PROJECT_NAME)
    project = project_name or os.getenv("LANGCHAIN_PROJECT", config_project)
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"))
    os.environ.setdefault("LANGSMITH_API_KEY", key)
    os.environ["LANGCHAIN_API_KEY"] = key  # always refresh in case key changed
    if enable_tracing:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

    try:
        client = client_cls(api_key=key)
    except Exception as exc:  # pragma: no cover - network/remote failures
        _LOGGER.warning("Failed to initialize LangSmith client: %s", exc)
        return None

    return client


if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from langsmith import Client


def traceable_node(name: str, func: _F) -> _F:
    """Decorate a callable with LangSmith tracing when available."""

    try:
        from langsmith.run_helpers import traceable
    except ImportError:  # pragma: no cover - optional dependency guard
        return func

    if getattr(func, _TRACE_ATTR, False):
        return func

    wrapped = traceable(name=name)(func)
    setattr(func, _TRACE_ATTR, True)
    setattr(wrapped, _TRACE_ATTR, True)
    return wrapped  # type: ignore[return-value]


__all__ = ["configure_langsmith", "traceable_node"]
