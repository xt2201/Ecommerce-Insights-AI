"""Rate limiting and API key authentication middleware.

This module provides:
- Token bucket rate limiting (in-memory, Redis-ready)
- API key authentication via X-API-Key header
- DDoS protection
- Cost control for LLM/SerpAPI calls
"""

from __future__ import annotations

import time
import hashlib
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable, Tuple
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_size: int = 20  # Max burst above rate limit
    block_duration_seconds: int = 60  # Block duration after exceeding limit


@dataclass 
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    tokens: float
    last_update: float = field(default_factory=time.time)
    refill_rate: float = 1.0  # tokens per second
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if rate limited
        """
        now = time.time()
        
        # Refill tokens based on time elapsed
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.capacity, self.tokens + elapsed * self.refill_rate)


class InMemoryRateLimiter:
    """In-memory rate limiter using token bucket algorithm.
    
    Thread-safe implementation suitable for single-instance deployments.
    For multi-instance deployments, use RedisRateLimiter instead.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = {}
        self._blocked: Dict[str, float] = {}  # client_id -> unblock_time
        self._lock = threading.Lock()
        
        # Calculate refill rate: requests_per_minute / 60 seconds
        self._refill_rate = self.config.requests_per_minute / 60.0
        
        logger.info(
            f"Rate limiter initialized: {self.config.requests_per_minute} req/min, "
            f"burst={self.config.burst_size}"
        )
    
    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create token bucket for client."""
        if client_id not in self._buckets:
            self._buckets[client_id] = TokenBucket(
                capacity=self.config.burst_size,
                tokens=self.config.burst_size,
                refill_rate=self._refill_rate,
            )
        return self._buckets[client_id]
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict]:
        """Check if request is allowed.
        
        Args:
            client_id: Client identifier (IP, API key, etc.)
            
        Returns:
            Tuple of (allowed, metadata)
        """
        with self._lock:
            now = time.time()
            
            # Check if client is blocked
            if client_id in self._blocked:
                unblock_time = self._blocked[client_id]
                if now < unblock_time:
                    remaining = int(unblock_time - now)
                    return False, {
                        "reason": "blocked",
                        "retry_after": remaining,
                        "message": f"Rate limit exceeded. Try again in {remaining}s",
                    }
                else:
                    del self._blocked[client_id]
            
            # Try to consume token
            bucket = self._get_bucket(client_id)
            if bucket.consume(1):
                return True, {
                    "remaining": int(bucket.available_tokens),
                    "limit": self.config.requests_per_minute,
                    "reset": int(60 - (now % 60)),
                }
            else:
                # Block client temporarily
                self._blocked[client_id] = now + self.config.block_duration_seconds
                return False, {
                    "reason": "rate_limited",
                    "retry_after": self.config.block_duration_seconds,
                    "message": "Rate limit exceeded",
                }
    
    def cleanup(self) -> int:
        """Clean up expired buckets and blocks.
        
        Returns:
            Number of items cleaned up
        """
        with self._lock:
            now = time.time()
            cleaned = 0
            
            # Clean expired blocks
            expired_blocks = [
                k for k, v in self._blocked.items() if now > v
            ]
            for k in expired_blocks:
                del self._blocked[k]
                cleaned += 1
            
            # Clean old buckets (not accessed in last hour)
            stale_buckets = [
                k for k, v in self._buckets.items() 
                if now - v.last_update > 3600
            ]
            for k in stale_buckets:
                del self._buckets[k]
                cleaned += 1
            
            return cleaned


class APIKeyAuth:
    """API key authentication handler.
    
    Validates X-API-Key header against configured API keys.
    In production, keys would be stored in a database.
    """
    
    def __init__(self, valid_keys: Optional[Dict[str, str]] = None):
        """Initialize API key auth.
        
        Args:
            valid_keys: Dict of api_key -> client_name
        """
        self._valid_keys = valid_keys or {}
        self._key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    
    def add_key(self, api_key: str, client_name: str) -> None:
        """Add a valid API key."""
        # Store hash of key for security
        key_hash = self._hash_key(api_key)
        self._valid_keys[key_hash] = client_name
    
    def remove_key(self, api_key: str) -> bool:
        """Remove an API key."""
        key_hash = self._hash_key(api_key)
        if key_hash in self._valid_keys:
            del self._valid_keys[key_hash]
            return True
        return False
    
    def validate_key(self, api_key: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate an API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, client_name)
        """
        if not api_key:
            return False, None
        
        key_hash = self._hash_key(api_key)
        if key_hash in self._valid_keys:
            return True, self._valid_keys[key_hash]
        
        # Check raw key (for backward compatibility during migration)
        if api_key in self._valid_keys:
            return True, self._valid_keys[api_key]
        
        return False, None
    
    @staticmethod
    def _hash_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting and API key auth.
    
    Usage:
        app.add_middleware(RateLimitMiddleware, config=RateLimitConfig())
    """
    
    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        api_key_auth: Optional[APIKeyAuth] = None,
        exempt_paths: Optional[list] = None,
        require_api_key: bool = False,
    ):
        """Initialize middleware.
        
        Args:
            app: FastAPI app
            config: Rate limit configuration
            api_key_auth: API key authentication handler
            exempt_paths: Paths exempt from rate limiting
            require_api_key: Whether to require API key for all requests
        """
        super().__init__(app)
        self.limiter = InMemoryRateLimiter(config)
        self.api_key_auth = api_key_auth or APIKeyAuth()
        self.exempt_paths = set(exempt_paths or ["/health", "/docs", "/openapi.json"])
        self.require_api_key = require_api_key
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting and auth."""
        path = request.url.path
        
        # Skip exempt paths
        if path in self.exempt_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # API key authentication
        api_key = request.headers.get("X-API-Key")
        is_valid_key, client_name = self.api_key_auth.validate_key(api_key)
        
        if self.require_api_key and not is_valid_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Valid X-API-Key header required",
                },
            )
        
        # Use API key client name for rate limiting if available
        if is_valid_key and client_name:
            client_id = f"key:{client_name}"
        
        # Check rate limit
        allowed, metadata = self.limiter.is_allowed(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": metadata.get("message", "Rate limit exceeded"),
                    "retry_after": metadata.get("retry_after", 60),
                },
                headers={
                    "Retry-After": str(metadata.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(self.limiter.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(metadata.get("reset", 60))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try X-Forwarded-For first (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()
        
        # Fall back to client host
        client = request.client
        if client:
            return client.host
        
        return "unknown"


# FastAPI dependency for rate limiting
def get_rate_limiter(
    config: Optional[RateLimitConfig] = None
) -> InMemoryRateLimiter:
    """Get rate limiter instance as FastAPI dependency."""
    return InMemoryRateLimiter(config)


def rate_limit_dependency(
    requests_per_minute: int = 100,
) -> Callable:
    """Create a rate limit dependency for specific endpoints.
    
    Usage:
        @app.get("/expensive", dependencies=[Depends(rate_limit_dependency(10))])
        async def expensive_endpoint():
            ...
    """
    limiter = InMemoryRateLimiter(
        RateLimitConfig(requests_per_minute=requests_per_minute)
    )
    
    async def check_rate_limit(request: Request):
        client_id = request.client.host if request.client else "unknown"
        allowed, metadata = limiter.is_allowed(client_id)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=metadata.get("message", "Rate limit exceeded"),
                headers={"Retry-After": str(metadata.get("retry_after", 60))},
            )
    
    return check_rate_limit


# API key dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    """FastAPI dependency that requires a valid API key.
    
    Usage:
        @app.get("/protected")
        async def protected_endpoint(api_key: str = Depends(require_api_key)):
            ...
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header required",
        )
    
    # In production, validate against database
    # For now, just check it's not empty
    if len(api_key) < 16:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )
    
    return api_key


__all__ = [
    "RateLimitConfig",
    "InMemoryRateLimiter",
    "APIKeyAuth",
    "RateLimitMiddleware",
    "get_rate_limiter",
    "rate_limit_dependency",
    "require_api_key",
]
