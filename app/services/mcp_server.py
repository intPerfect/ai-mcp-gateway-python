# -*- coding: utf-8 -*-
"""
MCP Server - 使用Python MCP官方SDK的MCP服务器
"""
import logging
from typing import Any, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp import type_extensions

from app.services.mcp_tool_registry import mcp_tool_registry

logger = logging.getLogger(__name__)

# 创建MCP服务器实例
mcp_server = Server("ai-mcp-gateway")


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    """
    列出所有已注册的工具
    MCP SDK会自动调用此方法返回工具列表
    """
    tool_defs = mcp_tool_registry.get_tool_definitions()
    
    tools = []
    for tool_def in tool_defs:
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["input_schema"]
        ))
    
    logger.info(f"MCP列出工具: {len(tools)} 个")
    return tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """
    调用工具
    MCP SDK会自动调用此方法执行工具
    """
    logger.info(f"MCP调用工具: {name}, 参数: {arguments}")
    
    try:
        # 执行工具
        result = await mcp_tool_registry.execute_tool(name, arguments)
        
        # 返回结果
        if isinstance(result, dict):
            content = json.dumps(result, ensure_ascii=False)
        elif isinstance(result, str):
            content = result
        else:
            content = str(result)
        
        return [TextContent(type="text", text=content)]
        
    except Exception as e:
        logger.error(f"工具调用异常: {name} - {str(e)}")
        return [TextContent(type="text", text=f"错误: {str(e)}")]


import json


async def run_stdio_server():
    """运行stdio模式服务器（用于本地MCP客户端连接）"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


def get_server() -> Server:
    """获取MCP服务器实例"""
    return mcp_server
