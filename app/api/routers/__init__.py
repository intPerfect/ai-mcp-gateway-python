# -*- coding: utf-8 -*-
"""
API Routers - 路由模块
"""
from app.api.routers.mcp_gateway import router as mcp_router
from app.api.routers.chat import router as chat_router
from app.api.routers.tools import router as tools_router
from app.api.routers.openapi import router as openapi_router
from app.api.routers.apikeys import router as apikeys_router
from app.api.routers.microservice import router as microservice_router

__all__ = ["mcp_router", "chat_router", "tools_router", "openapi_router", "apikeys_router", "microservice_router"]
