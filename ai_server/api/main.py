
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from ai_server.core.config import load_config, get_config_value
from ai_server.core.telemetry import configure_langsmith
from ai_server.api.dependencies import init_dependencies
from ai_server.api.routers import shopping, sessions, monitoring, debug
from ai_server.api.middleware import RateLimitMiddleware, RateLimitConfig, APIKeyAuth
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware."""
    # Get rate limit config from config.yaml or use defaults
    config = RateLimitConfig(
        requests_per_minute=get_config_value("security.rate_limit.requests_per_minute", 100),
        requests_per_hour=get_config_value("security.rate_limit.requests_per_hour", 1000),
        burst_size=get_config_value("security.rate_limit.burst_size", 20),
        block_duration_seconds=get_config_value("security.rate_limit.block_duration", 60),
    )
    
    # Setup API key auth
    api_key_auth = APIKeyAuth()
    
    # Add configured API keys (from environment)
    admin_key = os.getenv("ADMIN_API_KEY")
    if admin_key:
        api_key_auth.add_key(admin_key, "admin")
    
    # Exempt paths that don't need rate limiting
    exempt_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
    
    # Add middleware
    app.add_middleware(
        RateLimitMiddleware,
        config=config,
        api_key_auth=api_key_auth,
        exempt_paths=exempt_paths,
        require_api_key=get_config_value("security.require_api_key", False),
    )
    
    logger.info(f"Rate limiting enabled: {config.requests_per_minute} req/min")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting AI Server (Modular API)...")
    load_config()
    configure_langsmith()
    init_dependencies()
    
    logger.info("✅ AI Server ready!")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 Shutting down AI Server...")
    logger.info("=" * 80)

app = FastAPI(
    title="Amazon Smart Shopping Assistant API",
    description="AI-powered shopping assistant with 8 autonomous agents",
    version="2.1.0",
    lifespan=lifespan,
)

# Setup rate limiting (must be before CORS)
setup_rate_limiting(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(shopping.router, prefix="/api/shopping", tags=["Shopping"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(debug.router, prefix="/api/debug", tags=["Debug"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.1.0"}
