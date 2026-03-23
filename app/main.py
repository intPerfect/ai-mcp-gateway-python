"""
FastAPI Application Entry Point for MCP Gateway
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.mcp_gateway import router as mcp_router
from app.api.chat import websocket_handler, router as chat_router, load_tools_from_db
from app.api.tools import router as tools_router
from app.api.openapi_import import router as openapi_router
from app.api.apikeys import router as apikeys_router
from app.services.mcp_tool_registry import mcp_tool_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting MCP Gateway...")

    # 应用启动时预加载工具，避免第一次WebSocket连接时阻塞
    try:
        result = await load_tools_from_db()
        logger.info(
            f"启动时工具加载完成: registered={len(result.get('registered', []))}, failed={len(result.get('failed', []))}"
        )
    except Exception as e:
        logger.error(f"启动时加载工具失败: {e}")

    logger.info(f"MCP Gateway started on port {settings.server_port}")

    yield

    # Shutdown
    logger.info("Shutting down MCP Gateway...")
    logger.info("MCP Gateway stopped")


# Create FastAPI application
app = FastAPI(
    title="AI MCP Gateway",
    description="Python implementation of MCP (Model Context Protocol) Gateway",
    version="1.0.0",
    lifespan=lifespan,
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
    return {"service": "AI MCP Gateway", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    from app.utils.port_manager import PortManager
    import uvicorn

    # 清理端口
    port = settings.server_port
    PortManager.kill_port(port)

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=port,
        reload=False,
    )
