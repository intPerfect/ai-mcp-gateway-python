# -*- coding: utf-8 -*-
"""
API Routers - 路由模块
"""

from app.api.routers.mcp_gateway import router as mcp_router
from app.api.routers.chat import router as chat_router
from app.api.routers.tools import router as tools_router
from app.api.routers.openapi import router as openapi_router
from app.api.routers.microservice import router as microservice_router
from app.api.routers.gateway import router as gateway_router
from app.api.routers.apikeys import router as apikeys_router
from app.api.routers.auth import router as auth_router
from app.api.routers.user import router as user_router
from app.api.routers.role import router as role_router
from app.api.routers.permission import router as permission_router
from app.api.routers.business_line import router as business_line_router

__all__ = [
    "mcp_router",
    "chat_router",
    "tools_router",
    "openapi_router",
    "microservice_router",
    "gateway_router",
    "apikeys_router",
    "auth_router",
    "user_router",
    "role_router",
    "permission_router",
    "business_line_router",
]
