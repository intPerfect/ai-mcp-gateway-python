# -*- coding: utf-8 -*-
"""
MCP Tool Registry - 动态工具注册服务
从数据库读取接口配置，健康检查后动态注册MCP工具
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository import McpGatewayRepository
from app.infrastructure.models import McpGatewayTool, McpProtocolHttp

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None


@dataclass
class ToolStatus:
    """工具状态"""
    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    http_url: str
    error: Optional[str] = None


class McpToolRegistry:
    """MCP工具动态注册器"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_status: Dict[str, ToolStatus] = {}
        self._repository: Optional[McpGatewayRepository] = None
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ) -> bool:
        """注册工具"""
        if name in self._tools:
            logger.warning(f"工具已存在: {name}")
            return False
        
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
        logger.info(f"注册工具成功: {name}")
        return True
    
    def unregister_tool(self, name: str) -> bool:
        """注销工具"""
        if name not in self._tools:
            logger.warning(f"工具不存在: {name}")
            return False
        
        del self._tools[name]
        logger.info(f"注销工具成功: {name}")
        return True
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义列表（用于LLM）"""
        tools = []
        for tool in self._tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        return tools
    
    def get_tool_statuses(self) -> List[ToolStatus]:
        """获取所有工具状态"""
        return list(self._tool_status.values())
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"未知工具: {name}"}
        
        if not tool.handler:
            return {"error": f"工具无可用处理器: {name}"}
        
        try:
            result = await tool.handler(arguments)
            # 更新状态
            self._tool_status[name] = ToolStatus(
                name=name,
                status="healthy",
                http_url=self._tool_status.get(name, ToolStatus(name=name, status="unknown", http_url="")).http_url
            )
            return result
        except Exception as e:
            logger.error(f"工具执行异常: {name} - {str(e)}")
            # 更新状态
            self._tool_status[name] = ToolStatus(
                name=name,
                status="unhealthy",
                http_url=self._tool_status.get(name, ToolStatus(name=name, status="unknown", http_url="")).http_url,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def health_check(self, http_url: str, timeout: int = 5000) -> tuple[bool, str]:
        """
        健康检查HTTP接口
        
        Returns:
            (is_healthy, message)
        """
        try:
            async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                # 发送GET请求检查接口是否可用
                response = await client.get(http_url)
                if response.status_code < 500:
                    return True, f"OK (status: {response.status_code})"
                else:
                    return False, f"Server error: {response.status_code}"
        except httpx.TimeoutException:
            return False, "Timeout"
        except httpx.ConnectError:
            return False, "Connection failed"
        except Exception as e:
            return False, str(e)
    
    async def load_tools_from_db(
        self,
        db_session: AsyncSession,
        gateway_id: str = "gateway_001"
    ) -> Dict[str, Any]:
        """
        从数据库加载工具配置
        
        Args:
            db_session: 数据库会话
            gateway_id: 网关ID
        
        Returns:
            {"registered": [...], "failed": [...], "healthy": [...], "unhealthy": [...]}
        """
        self._repository = McpGatewayRepository(db_session)
        
        # 获取所有工具配置
        tools = await self._repository.get_tools_by_gateway_id(gateway_id)
        
        result = {
            "registered": [],
            "failed": [],
            "healthy": [],
            "unhealthy": []
        }
        
        for tool in tools:
            try:
                # 获取HTTP协议配置
                http_config = await self._repository.get_protocol_http_by_id(tool.protocol_id)
                if not http_config:
                    result["failed"].append({
                        "name": tool.tool_name,
                        "error": "HTTP配置不存在"
                    })
                    continue
                
                http_url = http_config.http_url
                http_method = http_config.http_method
                http_headers = self._parse_headers(http_config.http_headers)
                timeout = http_config.timeout
                
                # 健康检查
                is_healthy, health_msg = await self.health_check(http_url, timeout)
                
                tool_status = ToolStatus(
                    name=tool.tool_name,
                    status="healthy" if is_healthy else "unhealthy",
                    http_url=http_url,
                    error=None if is_healthy else health_msg
                )
                self._tool_status[tool.tool_name] = tool_status
                
                if is_healthy:
                    result["healthy"].append(tool.tool_name)
                else:
                    result["unhealthy"].append({
                        "name": tool.tool_name,
                        "error": health_msg
                    })
                
                # 获取参数映射构建input_schema
                mappings = await self._repository.get_protocol_mappings(tool.protocol_id, "request")
                input_schema = self._build_input_schema(mappings)
                
                # 创建动态handler
                handler = self._create_http_handler(
                    http_url=http_url,
                    http_method=http_method,
                    http_headers=http_headers,
                    timeout=timeout,
                    mappings=mappings
                )
                
                # 注册工具
                if self.register_tool(
                    name=tool.tool_name,
                    description=tool.tool_description,
                    input_schema=input_schema,
                    handler=handler
                ):
                    result["registered"].append(tool.tool_name)
                else:
                    result["failed"].append({
                        "name": tool.tool_name,
                        "error": "工具已存在"
                    })
                    
            except Exception as e:
                logger.error(f"加载工具失败: {tool.tool_name} - {str(e)}")
                result["failed"].append({
                    "name": tool.tool_name,
                    "error": str(e)
                })
        
        logger.info(f"工具加载完成: registered={len(result['registered'])}, "
                   f"healthy={len(result['healthy'])}, "
                   f"unhealthy={len(result['unhealthy'])}, "
                   f"failed={len(result['failed'])}")
        
        return result
    
    def _parse_headers(self, headers_json: Optional[str]) -> Dict[str, str]:
        """解析HTTP头"""
        if not headers_json:
            return {}
        try:
            return json.loads(headers_json)
        except:
            return {}
    
    def _build_input_schema(self, mappings: List) -> Dict[str, Any]:
        """构建JSON Schema"""
        if not mappings:
            return {"type": "object", "properties": {}, "required": []}
        
        from app.domain.session.message_handler import MessageHandler
        handler = MessageHandler.__new__(MessageHandler)
        return handler._build_input_schema(mappings)
    
    def _create_http_handler(
        self,
        http_url: str,
        http_method: str,
        http_headers: Dict[str, str],
        timeout: int,
        mappings: List
    ) -> Callable:
        """创建HTTP调用handler"""
        
        async def handler(args: Dict[str, Any]) -> Any:
            try:
                async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                    # 根据mappings构建请求
                    request_data = self._build_request_data(mappings, args)
                    
                    if http_method.upper() == "GET":
                        response = await client.get(
                            http_url,
                            params=request_data,
                            headers=http_headers
                        )
                    else:
                        response = await client.request(
                            method=http_method,
                            url=http_url,
                            json=request_data,
                            headers=http_headers
                        )
                    
                    if response.status_code < 400:
                        try:
                            return response.json()
                        except:
                            return {"data": response.text}
                    else:
                        return {"error": f"HTTP {response.status_code}: {response.text}"}
                        
            except httpx.TimeoutException:
                return {"error": "请求超时"}
            except httpx.ConnectError:
                return {"error": f"连接失败: {http_url}"}
            except Exception as e:
                return {"error": str(e)}
        
        return handler
    
    def _build_request_data(self, mappings: List, args: Dict[str, Any]) -> Dict[str, Any]:
        """根据mappings构建请求数据"""
        data = {}
        for mapping in mappings:
            field_name = mapping.field_name
            mcp_path = mapping.mcp_path
            
            if field_name in args:
                # 直接字段名
                data[mcp_path] = args[field_name]
            elif mcp_path in args:
                # MCP路径
                data[mcp_path] = args[mcp_path]
        
        return data


# 全局单例
mcp_tool_registry = McpToolRegistry()
