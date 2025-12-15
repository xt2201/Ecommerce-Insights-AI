"""Lightweight SerpAPI Amazon client with key rotation.

API key is loaded from environment (.env) with rotation support.
Configuration settings from config.yaml
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ai_server.core.config import ConfigurationError, get_config_value
from ai_server.core.api_key_manager import (
    get_serp_key,
    report_serp_error,
    report_serp_success
)
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


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
        
        import os
        # Mock mode controlled by environment variable only
        if os.getenv("MOCK_SEARCH", "").lower() == "true":
            logger.info("MOCK_SEARCH enabled: returning mock data")
            try:
                import json
                from pathlib import Path
                mock_path = Path("data/mock_search_results.json")
                if mock_path.exists():
                    time.sleep(float(os.getenv("MOCK_SEARCH_DELAY", "0.5")))
                    with open(mock_path) as f:
                        mock_items = json.load(f)
                        
                    # Filter mock items by query roughly
                    query = str(params.get('q', '')).lower()
                    
                    if query == "fail_test":
                        return {"organic_results": []}
                        
                    return {
                        "organic_results": mock_items,
                        "search_metadata": {
                            "status": "Success",
                            "total_results": len(mock_items)
                        }
                    }
            except Exception as e:
                logger.error(f"Failed to load mock data: {e}")
        
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
                        # Report error to rotation manager
                        is_rate_limit = exc.response.status_code == 429
                        report_serp_error(api_key, is_rate_limit=is_rate_limit)
                        raise SerpAPIError(f"SerpAPI Client Error: {exc} - Body: {exc.response.text}") from exc
                last_error = exc
            else:
                if payload.get("error"):
                    error_msg = payload["error"]
                    logger.error(f"SerpAPI returned error: {error_msg}")
                    # Report error to rotation manager
                    report_serp_error(api_key, is_rate_limit="rate" in str(error_msg).lower())
                    last_error = SerpAPIError(str(error_msg))
                else:
                    # Success - report to rotation manager
                    report_serp_success(api_key)
                    return payload

            if attempt < self._settings.max_retries:
                time.sleep(self._settings.retry_backoff_seconds)

        logger.error("SerpAPI request failed after retries")
        raise SerpAPIError("SerpAPI request failed") from last_error

    def _resolve_api_key(self) -> str:
        """Get SerpAPI key using rotation manager."""
        try:
            return get_serp_key()
        except ValueError as exc:
            raise SerpAPIError("SerpAPI API key missing from environment") from exc


__all__ = ["SerpAPIClient", "SerpAPIError", "SerpAPISettings"]
