# -*- coding: utf-8 -*-
"""
Infrastructure Database - 数据库基础设施
"""
from app.infrastructure.database.connection import (
    async_session_factory,
    get_db_session,
    engine,
    Base,
    init_db
)
from app.infrastructure.database.models import (
    McpGateway,
    McpGatewayAuth,
    McpGatewayTool,
    McpProtocolHttp,
    McpProtocolMapping
)
# 兼容层：保持原有导入不变
from app.infrastructure.database.repository import McpGatewayRepository, RbacRepository

__all__ = [
    "async_session_factory", "get_db_session", "engine", "Base", "init_db",
    "McpGateway", "McpGatewayAuth", "McpGatewayTool",
    "McpProtocolHttp", "McpProtocolMapping",
    "McpGatewayRepository", "RbacRepository",
]
