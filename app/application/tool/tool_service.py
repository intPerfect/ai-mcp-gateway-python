# -*- coding: utf-8 -*-
"""
Tool Service - 工具应用服务
工具管理用例编排
"""
import logging
from typing import Any, Dict, List

from app.domain.tool.registry import McpToolRegistry
from app.domain.tool.models import ToolDefinition, ToolStatus

logger = logging.getLogger(__name__)


class ToolService:
    """工具应用服务"""
    
    def __init__(self):
        self._registry = McpToolRegistry()
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler
    ) -> bool:
        """注册工具"""
        return self._registry.register_tool(name, description, input_schema, handler)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """获取所有工具"""
        return self._registry.get_all_tools()
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义列表"""
        return self._registry.get_tool_definitions()
    
    def get_tool_statuses(self) -> List[ToolStatus]:
        """获取工具状态"""
        return self._registry.get_tool_statuses()
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        return await self._registry.execute_tool(name, arguments)
    
    async def load_tools_from_db(self, db_session, gateway_id: str = "gateway_001") -> Dict[str, Any]:
        """从数据库加载工具"""
        return await self._registry.load_tools_from_db(db_session, gateway_id)


# 全局单例
tool_service = ToolService()
