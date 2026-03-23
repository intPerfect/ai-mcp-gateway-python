# -*- coding: utf-8 -*-
"""
Tools Router - 工具管理路由
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.services.mcp_tool_registry import mcp_tool_registry
from app.utils.result import Result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tools")
async def list_tools():
    """获取所有已注册的工具"""
    tools = mcp_tool_registry.get_all_tools()
    return Result.success({
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in tools
        ],
        "total": len(tools)
    })


@router.get("/tools/status")
async def get_tools_status():
    """获取所有工具状态"""
    statuses = mcp_tool_registry.get_tool_statuses()
    return Result.success({
        "tools": [
            {
                "name": status.name,
                "status": status.status,
                "http_url": status.http_url,
                "error": status.error
            }
            for status in statuses
        ],
        "total": len(statuses)
    })


@router.post("/tools/reload")
async def reload_tools(
    gateway_id: str = "gateway_001",
    db: AsyncSession = Depends(get_db_session)
):
    """重新加载工具"""
    result = await mcp_tool_registry.load_tools_from_db(db, gateway_id)
    return Result.success(result)


@router.get("/tools/{tool_name}/status")
async def get_tool_status(tool_name: str):
    """获取单个工具的详细状态"""
    try:
        tool = mcp_tool_registry.get_tool(tool_name)
        if not tool:
            return Result.not_found(f"工具不存在: {tool_name}")

        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        status = statuses.get(tool_name)

        return Result.success({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "status": status.status if status else "unknown",
            "http_url": status.http_url if status else "",
            "error": status.error if status else None,
        })
    except Exception as e:
        logger.error(f"获取工具状态失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/tools/{tool_name}/health-check")
async def health_check_tool(
    tool_name: str,
    db: AsyncSession = Depends(get_db_session)
):
    """对指定工具进行健康检查"""
    try:
        from app.infrastructure.database import McpGatewayRepository

        repository = McpGatewayRepository(db)
        tool = await repository.get_tool_by_name("gateway_001", tool_name)

        if not tool:
            return Result.not_found(f"工具不存在: {tool_name}")

        http_config = await repository.get_protocol_http_by_id(tool.protocol_id)
        if not http_config:
            return Result.not_found("HTTP配置不存在")

        is_healthy, message = await mcp_tool_registry.health_check(
            http_config.http_url,
            http_config.timeout
        )

        # 更新状态
        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        if tool_name in statuses:
            statuses[tool_name].status = "healthy" if is_healthy else "unhealthy"
            statuses[tool_name].error = None if is_healthy else message

        return Result.success({
            "name": tool_name,
            "healthy": is_healthy,
            "message": message,
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return Result.internal_error(str(e))
