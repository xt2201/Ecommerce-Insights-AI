"""Fallback LLM wrapper with automatic provider switching on errors."""

import logging
from copy import deepcopy
from typing import Any, List, Tuple, Iterator
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)


class FallbackLLM(Runnable):
    """LLM wrapper that automatically switches providers on errors.
    
    When primary provider fails (rate limit, API error, etc.), automatically
    tries fallback providers in order until one succeeds.
    
    Extends Runnable to be compatible with LangChain LCEL chains (pipe operator |).
    """
    
    # Error types that trigger fallback
    FALLBACK_ERRORS: Tuple[str, ...] = (
        "RateLimitError",
        "APIError", 
        "ServiceUnavailableError",
        "APIConnectionError",
        "Timeout",
        "KeyError",
        "ValidationError",
        "OutputParserException",
    )
    
    def __init__(self, primary_llm: BaseChatModel, fallback_llms: List[BaseChatModel]):
        """Initialize FallbackLLM.
        
        Args:
            primary_llm: Primary LLM provider
            fallback_llms: List of fallback providers (tried in order)
        """
        super().__init__()
        self.primary_llm = primary_llm
        self.fallback_llms = fallback_llms or []
        self.current_llm = primary_llm
        self._current_provider = "primary"
        self._llm_type = f"fallback_{primary_llm._llm_type}"
    
    def _should_fallback(self, error: Exception) -> bool:
        """Check if error should trigger fallback."""
        error_type = type(error).__name__
        return any(err_name in error_type for err_name in self.FALLBACK_ERRORS)
    
    def _execute_with_fallback(self, method_name: str, *args, **kwargs) -> Any:
        """Execute method with automatic fallback on error.
        
        Args:
            method_name: Name of method to call on LLM
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from successful provider
            
        Raises:
            Exception: If all providers fail
        """
        # Build provider list
        providers_to_try = [
            (self.primary_llm, "primary"),
            *[(llm, f"fallback_{i}") for i, llm in enumerate(self.fallback_llms)]
        ]
        
        last_error = None
        
        for llm, provider_name in providers_to_try:
            try:
                # Get method and call it
                method = getattr(llm, method_name)
                result = method(*args, **kwargs)
                
                # Success! Update current provider if switched
                if provider_name != self._current_provider:
                    logger.warning(
                        f"🔄 Switched from {self._current_provider} to {provider_name} "
                        f"for {method_name}() due to previous errors"
                    )
                    self._current_provider = provider_name
                    self.current_llm = llm
                
                return result
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                
                # Check if should fallback
                if self._should_fallback(e):
                    logger.warning(
                        f"⚠️  Provider {provider_name} failed with {error_type}: {str(e)[:100]}"
                    )
                    continue  # Try next provider
                else:
                    # Non-fallback error, raise immediately
                    logger.error(f"❌ Provider {provider_name} failed with non-recoverable error")
                    raise
        
        # All providers failed
        logger.error("❌ All LLM providers failed!")
        raise last_error or Exception("All LLM providers failed")
    
    # Implement Runnable interface
    def invoke(
        self, 
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any
    ) -> Any:
        """Invoke LLM with fallback (Runnable interface).
        
        Args:
            input: Input to the runnable (messages or dict)
            config: Runnable configuration
            **kwargs: Additional arguments
            
        Returns:
            Response from LLM
        """
        return self._execute_with_fallback("invoke", input, config=config, **kwargs)
    
    def with_structured_output(self, schema: Any, **kwargs):
        """Return LLM configured for structured output with fallback.
        
        Creates a wrapper that provides fallback for structured output calls.
        """
        class StructuredFallbackWrapper:
            def __init__(self, parent: "FallbackLLM", schema: Any, **structured_kwargs):
                self.parent = parent
                self.schema = schema
                self.structured_kwargs = structured_kwargs
            
            def invoke(self, *args, **invoke_kwargs):
                """Invoke structured output with fallback."""
                original_config = invoke_kwargs.pop("config", None)
                base_config = self._ensure_non_streaming_config(original_config)
                # Build provider list
                providers_to_try = [
                    (self.parent.primary_llm, "primary"),
                    *[(llm, f"fallback_{i}") for i, llm in enumerate(self.parent.fallback_llms)]
                ]
                
                last_error = None
                
                for llm, provider_name in providers_to_try:
                    try:
                        # Get structured LLM and invoke
                        structured_llm = llm.with_structured_output(
                            self.schema, **self.structured_kwargs
                        )
                        result = structured_llm.invoke(
                            *args,
                            config=deepcopy(base_config),
                            **invoke_kwargs,
                        )
                        
                        # Check if include_raw=True (result is dict with 'parsed' key)
                        if isinstance(result, dict) and "parsed" in result:
                            # If parsed is None, treat as parsing failure
                            if result["parsed"] is None:
                                logger.warning(
                                    f"⚠️  Provider {provider_name} returned None for structured output, "
                                    f"trying next provider"
                                )
                                # Treat None result as error, continue to next provider
                                continue
                        
                        # Success!
                        if provider_name != self.parent._current_provider:
                            logger.warning(
                                f"🔄 Switched to {provider_name} for structured output"
                            )
                            self.parent._current_provider = provider_name
                            self.parent.current_llm = llm
                        
                        return result
                        
                    except Exception as e:
                        last_error = e
                        if self.parent._should_fallback(e):
                            logger.warning(
                                f"⚠️  Structured output provider {provider_name} failed: "
                                f"{type(e).__name__}"
                            )
                            continue
                        else:
                            raise
                
                # All failed
                logger.error("❌ All providers failed for structured output")
                raise last_error or Exception("All providers failed")

            @staticmethod
            def _ensure_non_streaming_config(config: Any) -> dict:
                """Force stream=False to satisfy providers that disallow streaming with JSON schemas."""
                if config is None:
                    return {"configurable": {"stream": False}}
                safe_config = deepcopy(config)
                configurable = dict(safe_config.get("configurable", {}))
                configurable["stream"] = False
                safe_config["configurable"] = configurable
                return safe_config
        
        return StructuredFallbackWrapper(self, schema, **kwargs)
    
    def __getattr__(self, name: str):
        """Delegate any other method calls to current LLM with fallback."""
        if name.startswith("_"):
            # Avoid infinite recursion for private attributes
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
        
        def method_wrapper(*args, **kwargs):
            return self._execute_with_fallback(name, *args, **kwargs)
        
        return method_wrapper
