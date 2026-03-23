# -*- coding: utf-8 -*-
"""
Tools Management API - 工具管理接口
提供工具列表、健康检查、重新加载等功能
"""
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.services.mcp_tool_registry import mcp_tool_registry

logger = logging.getLogger(__name__)

router = APIRouter()


def success_response(data: Any = None, info: str = "success") -> Dict:
    """构建成功响应"""
    return {"code": "0000", "info": info, "data": data}


def fail_response(code: str, info: str) -> Dict:
    """构建失败响应"""
    return {"code": code, "info": info}


@router.get("/tools")
async def list_tools() -> Dict:
    """
    获取所有工具列表及状态
    
    Returns:
        工具列表，包括名称、描述、输入模式、状态等
    """
    try:
        tools = mcp_tool_registry.get_tool_definitions()
        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        
        tool_list = []
        for tool in tools:
            status = statuses.get(tool["name"])
            tool_list.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
                "status": status.status if status else "unknown",
                "http_url": status.http_url if status else "",
                "error": status.error if status else None
            })
        
        return success_response({
            "total": len(tool_list),
            "tools": tool_list
        })
        
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        return fail_response(code="INTERNAL_ERROR", info=str(e))


@router.post("/tools/reload")
async def reload_tools(
    gateway_id: str = "gateway_001",
    db: AsyncSession = Depends(get_db_session)
) -> Dict:
    """
    重新从数据库加载工具
    
    Args:
        gateway_id: 网关ID
    
    Returns:
        加载结果
    """
    try:
        # 清空现有工具
        for tool in mcp_tool_registry.get_all_tools():
            mcp_tool_registry.unregister_tool(tool.name)
        
        # 从数据库重新加载
        result = await mcp_tool_registry.load_tools_from_db(db, gateway_id)
        
        return success_response({
            "message": "工具重新加载完成",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"重新加载工具失败: {str(e)}")
        return fail_response(code="INTERNAL_ERROR", info=str(e))


@router.get("/tools/{tool_name}/status")
async def get_tool_status(tool_name: str) -> Dict:
    """
    获取单个工具的状态
    
    Args:
        tool_name: 工具名称
    """
    try:
        tool = mcp_tool_registry.get_tool(tool_name)
        if not tool:
            return fail_response(code="NOT_FOUND", info=f"工具不存在: {tool_name}")
        
        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        status = statuses.get(tool_name)
        
        return success_response({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "status": status.status if status else "unknown",
            "http_url": status.http_url if status else "",
            "error": status.error if status else None
        })
        
    except Exception as e:
        logger.error(f"获取工具状态失败: {str(e)}")
        return fail_response(code="INTERNAL_ERROR", info=str(e))


@router.post("/tools/{tool_name}/health-check")
async def health_check_tool(
    tool_name: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict:
    """
    对指定工具进行健康检查
    
    Args:
        tool_name: 工具名称
    """
    try:
        from app.infrastructure.database import McpGatewayRepository
        
        repository = McpGatewayRepository(db)
        tool = await repository.get_tool_by_name("gateway_001", tool_name)
        
        if not tool:
            return fail_response(code="NOT_FOUND", info=f"工具不存在: {tool_name}")
        
        http_config = await repository.get_protocol_http_by_id(tool.protocol_id)
        if not http_config:
            return fail_response(code="NOT_FOUND", info="HTTP配置不存在")
        
        is_healthy, message = await mcp_tool_registry.health_check(
            http_config.http_url,
            http_config.timeout
        )
        
        # 更新状态
        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        if tool_name in statuses:
            statuses[tool_name].status = "healthy" if is_healthy else "unhealthy"
            statuses[tool_name].error = None if is_healthy else message
        
        return success_response({
            "name": tool_name,
            "healthy": is_healthy,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return fail_response(code="INTERNAL_ERROR", info=str(e))
