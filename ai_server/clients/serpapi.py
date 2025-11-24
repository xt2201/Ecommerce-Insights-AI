"""Lightweight SerpAPI Amazon client.

API key is loaded from environment (.env)
Configuration settings from config.yaml
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ai_server.core.config import ConfigurationError, get_api_key, get_config_value

logger = logging.getLogger(__name__)


class SerpAPIError(RuntimeError):
    """Raised when SerpAPI returns an error payload or transport failure occurs."""


@dataclass(frozen=True)
class SerpAPISettings:
    base_url: str = "https://serpapi.com/search.json"
    max_retries: int = 2
    retry_backoff_seconds: float = 1.5


class SerpAPIClient:
    """Client wrapper that exposes typed helpers for Amazon endpoints."""

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        settings: SerpAPISettings | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._settings = settings or SerpAPISettings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search_products(self, **params: Any) -> Dict[str, Any]:
        """Perform a generic Amazon search query."""
        
        # SerpAPI Amazon engine uses 'k' parameter for keyword search
        if 'q' in params:
            params['k'] = params.pop('q')
        
        # Get engine from config
        engine = get_config_value("serpapi.engine", "amazon")
        
        payload = {"engine": engine, **params}
        return self._perform_request(payload)

    def get_product_details(self, *, asin: str, **params: Any) -> Dict[str, Any]:
        """Fetch detailed information for a given ASIN."""

        if not asin:
            raise ValueError("asin must be provided")
        payload = {"engine": "amazon_product", "product_id": asin, **params}
        return self._perform_request(payload)

    def get_product_reviews(self, *, asin: str, **params: Any) -> Dict[str, Any]:
        """Fetch product reviews for a given ASIN."""

        if not asin:
            raise ValueError("asin must be provided")
        payload = {"engine": "amazon_product_reviews", "product_id": asin, **params}
        return self._perform_request(payload)

    def get_product_offers(self, *, asin: str, **params: Any) -> Dict[str, Any]:
        """Fetch product offers (sellers) for a given ASIN."""

        if not asin:
            raise ValueError("asin must be provided")
        payload = {"engine": "amazon_offers", "product_id": asin, **params}
        return self._perform_request(payload)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _perform_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = self._resolve_api_key()
        complete_params = {"api_key": api_key, **params}
        
        # Get timeout from config
        timeout = get_config_value("serpapi.timeout", 30)
        
        # Mask API key for logging
        log_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.debug(f"SerpAPI Request: {self._settings.base_url} - Params: {log_params}")

        last_error: Exception | None = None
        for attempt in range(1, self._settings.max_retries + 1):
            try:
                response = self._session.get(
                    self._settings.base_url, 
                    params=complete_params, 
                    timeout=timeout
                )
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as exc:  # pragma: no cover - network errors in tests
                logger.warning(f"SerpAPI attempt {attempt} failed: {exc}")
                if hasattr(exc, 'response') and exc.response is not None:
                    logger.warning(f"SerpAPI Error Body: {exc.response.text}")
                    # Do not retry on 4xx client errors
                    if 400 <= exc.response.status_code < 500:
                        raise SerpAPIError(f"SerpAPI Client Error: {exc}") from exc
                last_error = exc
            else:
                if payload.get("error"):
                    error_msg = payload["error"]
                    logger.error(f"SerpAPI returned error: {error_msg}")
                    last_error = SerpAPIError(str(error_msg))
                else:
                    return payload

            if attempt < self._settings.max_retries:
                time.sleep(self._settings.retry_backoff_seconds)

        logger.error("SerpAPI request failed after retries")
        raise SerpAPIError("SerpAPI request failed") from last_error

    def _resolve_api_key(self) -> str:
        """Get SerpAPI key from environment."""
        try:
            return get_api_key("SERP_API_KEY")
        except ConfigurationError as exc:  # pragma: no cover - configuration validated elsewhere
            raise SerpAPIError("SerpAPI API key missing from environment") from exc


__all__ = ["SerpAPIClient", "SerpAPIError", "SerpAPISettings"]
