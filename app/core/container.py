# -*- coding: utf-8 -*-
"""
Dependency Injection Container - 依赖注入容器
实现简单的服务容器模式，替代全局单例
"""

from typing import Dict, Type, Any, Callable, Optional
from functools import lru_cache


class ServiceContainer:
    """服务容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register_instance(self, name: str, instance: Any) -> None:
        """注册已存在的实例"""
        self._services[name] = instance
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """注册工厂函数"""
        self._factories[name] = factory
    
    def register_singleton(self, name: str, factory: Callable) -> None:
        """注册单例工厂"""
        self._factories[name] = factory
        # 标记为单例
        self._singletons[name] = None
    
    def get(self, name: str) -> Any:
        """获取服务实例"""
        # 优先返回已注册的实例
        if name in self._services:
            return self._services[name]
        
        # 检查是否是单例
        if name in self._singletons:
            if self._singletons[name] is not None:
                return self._singletons[name]
            
            # 创建单例实例
            if name in self._factories:
                instance = self._factories[name]()
                self._singletons[name] = instance
                return instance
        
        # 使用工厂创建新实例
        if name in self._factories:
            return self._factories[name]()
        
        raise KeyError(f"Service '{name}' not found in container")
    
    def has(self, name: str) -> bool:
        """检查服务是否已注册"""
        return name in self._services or name in self._factories
    
    def clear(self) -> None:
        """清空容器"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


# 全局容器实例
_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """获取全局容器实例"""
    return _container


def register_service(name: str, instance: Any) -> None:
    """注册服务实例"""
    _container.register_instance(name, instance)


def register_factory(name: str, factory: Callable) -> None:
    """注册服务工厂"""
    _container.register_factory(name, factory)


def register_singleton(name: str, factory: Callable) -> None:
    """注册单例服务"""
    _container.register_singleton(name, factory)


def get_service(name: str) -> Any:
    """获取服务实例"""
    return _container.get(name)


# FastAPI 依赖注入辅助函数

def get_llm_service():
    """获取 LLM 服务实例"""
    from app.services.llm_service import LLMService
    if not _container.has("llm_service"):
        _container.register_singleton("llm_service", LLMService)
    return _container.get("llm_service")


def get_chat_service():
    """获取 Chat 服务实例"""
    from app.services.chat_service import ChatService
    if not _container.has("chat_service"):
        _container.register_singleton("chat_service", ChatService)
    return _container.get("chat_service")


def get_react_agent():
    """获取 ReAct Agent 实例"""
    from app.services.react_agent import ReActAgent
    if not _container.has("react_agent"):
        _container.register_singleton("react_agent", ReActAgent)
    return _container.get("react_agent")


def get_mcp_tool_registry():
    """获取 MCP 工具注册表实例"""
    from app.services.mcp_tool_registry import McpToolRegistry
    if not _container.has("mcp_tool_registry"):
        _container.register_singleton("mcp_tool_registry", McpToolRegistry)
    return _container.get("mcp_tool_registry")


def get_session_manager():
    """获取会话管理器实例"""
    from app.domain.session.service import SessionManagementService
    if not _container.has("session_manager"):
        _container.register_singleton("session_manager", SessionManagementService)
    return _container.get("session_manager")


def get_conversation_logger():
    """获取对话日志记录器实例"""
    from app.infrastructure.logging.conversation_logger import ConversationLogger
    if not _container.has("conversation_logger"):
        _container.register_singleton("conversation_logger", ConversationLogger)
    return _container.get("conversation_logger")


# 初始化默认服务
def init_services():
    """初始化所有默认服务"""
    # 预注册服务
    get_llm_service()
    get_react_agent()
    get_mcp_tool_registry()
    get_session_manager()
    get_conversation_logger()