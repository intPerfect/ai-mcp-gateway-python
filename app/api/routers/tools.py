# -*- coding: utf-8 -*-
"""
Tools Router - 工具管理路由
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.services.mcp_tool_registry import mcp_tool_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tools")
async def list_tools():
    """获取所有已注册的工具"""
    tools = mcp_tool_registry.get_all_tools()
    return {
        "code": "0000",
        "info": "success",
        "data": {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema
                }
                for tool in tools
            ],
            "total": len(tools)
        }
    }


@router.get("/tools/status")
async def get_tools_status():
    """获取所有工具状态"""
    statuses = mcp_tool_registry.get_tool_statuses()
    return {
        "code": "0000",
        "info": "success",
        "data": {
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
        }
    }


@router.post("/tools/reload")
async def reload_tools(
    gateway_id: str = "gateway_001",
    db: AsyncSession = Depends(get_db_session)
):
    """重新加载工具"""
    result = await mcp_tool_registry.load_tools_from_db(db, gateway_id)
    return {
        "code": "0000",
        "info": "success",
        "data": result
    }
