"""
FastAPI Application Entry Point for MCP Gateway
"""

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "gateway_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "gateway.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        },
        "uvicorn_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "uvicorn.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "default",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "gateway_file"],
            "level": logging.INFO,
        },
        "uvicorn": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console", "uvicorn_file"],
            "level": logging.INFO,
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
from app.config import get_settings
from app.api.routers import (
    mcp_router,
    chat_router,
    tools_router,
    openapi_router,
    microservice_router,
    gateway_router,
    auth_router,
    user_router,
    role_router,
    permission_router,
    business_line_router,
)
from app.api.routers.admin import router as admin_router
from app.api.routers.chat import websocket_handler
from app.utils.exceptions import AppException
from app.utils.result import Result

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MCP Gateway...")
    logger.info(f"MCP Gateway started on port {settings.server_port}")

    yield

    logger.info("Shutting down MCP Gateway...")
    logger.info("MCP Gateway stopped")


app = FastAPI(
    title="AI MCP Gateway",
    description="Python implementation of MCP (Model Context Protocol) Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 全局异常处理器 ============


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """AppException 统一处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=Result.error(exc.code, exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """参数验证异常统一处理"""
    return JSONResponse(
        status_code=422,
        content=Result.error("VALIDATION_ERROR", str(exc)).model_dump(),
    )

app.include_router(mcp_router, prefix="/api-gateway", tags=["MCP Gateway"])
app.include_router(tools_router, prefix="/api", tags=["Tools"])
app.include_router(openapi_router, prefix="/api", tags=["OpenAPI Import"])
app.include_router(gateway_router, prefix="/api", tags=["Gateway Management"])
app.include_router(microservice_router, prefix="/api", tags=["Microservice"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(user_router, tags=["User"])
app.include_router(role_router, tags=["Role"])
app.include_router(permission_router, tags=["Permission"])
app.include_router(business_line_router, tags=["Business Line"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket_handler(websocket)


@app.get("/")
async def root():
    return {"service": "AI MCP Gateway", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    from app.utils.port_manager import PortManager
    import uvicorn

    port = settings.server_port
    PortManager.kill_port(port)

    # 设置环境变量控制热更新
    import os

    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=port,
        reload=reload,
        reload_dirs=["app"] if reload else None,
    )
