
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from ai_server.core.config import load_config
from ai_server.core.telemetry import configure_langsmith
from ai_server.api.dependencies import init_dependencies
from ai_server.api.routers import shopping, sessions, monitoring, debug
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)

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
    description="AI-powered shopping assistant with 4 autonomous agents",
    version="2.0.0",
    lifespan=lifespan,
)

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
    return {"status": "healthy", "version": "2.0.0"}
