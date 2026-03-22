# -*- coding: utf-8 -*-
"""
Core Module - 核心模块
包含依赖注入容器、配置等核心功能
"""

from .container import (
    ServiceContainer,
    get_container,
    register_service,
    register_factory,
    register_singleton,
    get_service,
    get_llm_service,
    get_chat_service,
    get_react_agent,
    get_mcp_tool_registry,
    get_session_manager,
)

__all__ = [
    "ServiceContainer",
    "get_container",
    "register_service",
    "register_factory",
    "register_singleton",
    "get_service",
    "get_llm_service",
    "get_chat_service",
    "get_react_agent",
    "get_mcp_tool_registry",
    "get_session_manager",
]