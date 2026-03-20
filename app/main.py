"""
FastAPI Application Entry Point for MCP Gateway
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.mcp_gateway import router as mcp_router
from app.api.chat import websocket_handler, router as chat_router
from app.api.tools import router as tools_router
from app.api.openapi_import import router as openapi_router
from app.api.apikeys import router as apikeys_router
from app.domain.session import session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting MCP Gateway...")
    await session_manager.start()
    logger.info(f"MCP Gateway started on port {settings.server_port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Gateway...")
    await session_manager.stop()
    logger.info("MCP Gateway stopped")


# Create FastAPI application
app = FastAPI(
    title="AI MCP Gateway",
    description="Python implementation of MCP (Model Context Protocol) Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(mcp_router, prefix="/api-gateway", tags=["MCP Gateway"])
app.include_router(tools_router, prefix="/api", tags=["Tools"])
app.include_router(openapi_router, prefix="/api", tags=["OpenAPI Import"])
app.include_router(apikeys_router, prefix="/api", tags=["API Keys"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])

# WebSocket endpoint
@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket_handler(websocket)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI MCP Gateway",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
