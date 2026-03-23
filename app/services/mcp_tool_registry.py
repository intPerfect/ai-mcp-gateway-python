# -*- coding: utf-8 -*-
"""
MCP Tool Registry v3.0 - 动态工具注册服务
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
        """注册工具（静默注册，不输出单条日志）"""
        if name in self._tools:
            return False
        
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
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
        """获取工具定义列表（用于LLM - Anthropic格式）"""
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
            self._tool_status[name] = ToolStatus(
                name=name,
                status="unhealthy",
                http_url=self._tool_status.get(name, ToolStatus(name=name, status="unknown", http_url="")).http_url,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def health_check(self, http_url: str, timeout: int = 5000) -> tuple[bool, str]:
        """健康检查HTTP接口"""
        try:
            async with httpx.AsyncClient(timeout=timeout / 1000) as client:
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
        """从数据库加载工具配置"""
        self._repository = McpGatewayRepository(db_session)
        
        tools = await self._repository.get_tools_by_gateway_id(gateway_id)
        
        result = {
            "registered": [],
            "failed": [],
            "healthy": [],
            "unhealthy": []
        }
        
        for tool in tools:
            try:
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

                self._tool_status[tool.tool_name] = ToolStatus(
                    name=tool.tool_name,
                    status="unknown",
                    http_url=http_url
                )
                result["healthy"].append(tool.tool_name)
                
                # 获取所有参数映射
                mappings = await self._repository.get_protocol_mappings(tool.protocol_id)
                input_schema = self._build_input_schema(mappings)
                
                # 创建动态handler
                handler = self._create_http_handler(
                    http_url=http_url,
                    http_method=http_method,
                    http_headers=http_headers,
                    timeout=timeout,
                    mappings=mappings
                )
                
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
        
        # 输出一行汇总日志
        tools_str = ', '.join(result['registered'][:5])
        if len(result['registered']) > 5:
            tools_str += f" 等{len(result['registered'])}个"
        logger.info(f"注册MCP工具: [{tools_str}]")
        
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
        """
        构建JSON Schema
        
        排除path参数（从URL模板解析）
        """
        if not mappings:
            return {"type": "object", "properties": {}, "required": []}
        
        # 过滤：排除path参数
        input_mappings = [
            m for m in mappings 
            if m.param_location != "path"
        ]
        
        # 按sort_order排序
        sorted_mappings = sorted(input_mappings, key=lambda x: x.sort_order or 0)
        
        properties = {}
        required = []
        
        for mapping in sorted_mappings:
            prop = {"type": mapping.field_type}
            
            if mapping.field_desc:
                prop["description"] = mapping.field_desc
            
            if mapping.enum_values:
                try:
                    enum_list = json.loads(mapping.enum_values)
                    prop["enum"] = enum_list
                except:
                    pass
            
            if mapping.default_value:
                prop["default"] = mapping.default_value
            
            properties[mapping.field_name] = prop
            
            if mapping.is_required == 1:
                required.append(mapping.field_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required if required else None,
            "additionalProperties": False
        }
    
    def _create_http_handler(
        self,
        http_url: str,
        http_method: str,
        http_headers: Dict[str, str],
        timeout: int,
        mappings: List
    ) -> Callable:
        """
        创建HTTP调用handler
        
        支持多种参数位置：path/query/body/form/header
        """
        
        async def handler(args: Dict[str, Any]) -> Any:
            try:
                async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                    # 根据mappings构建请求数据
                    request_parts = self._build_request_parts(mappings, args)
                    
                    # 替换URL路径参数
                    final_url = http_url
                    for key, value in request_parts["path"].items():
                        placeholder = f"{{{key}}}"
                        if placeholder in final_url:
                            final_url = final_url.replace(placeholder, str(value))
                    
                    # 获取查询参数和请求体
                    query_params = request_parts["query"]
                    body_data = request_parts["body"]
                    form_data = request_parts["form"]
                    header_params = request_parts["header"]
                    
                    # 合并header
                    final_headers = {**http_headers, **header_params}
                    
                    if http_method.upper() == "GET":
                        response = await client.get(
                            final_url,
                            params=query_params,
                            headers=final_headers
                        )
                    elif form_data:
                        response = await client.request(
                            method=http_method,
                            url=final_url,
                            data=form_data,
                            params=query_params,
                            headers=final_headers
                        )
                    else:
                        response = await client.request(
                            method=http_method,
                            url=final_url,
                            json=body_data if body_data else None,
                            params=query_params if query_params else None,
                            headers=final_headers
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
    
    def _build_request_parts(self, mappings: List, args: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        根据mappings构建请求数据，按参数位置分类
        
        Returns:
            Dict with keys: 'path', 'query', 'body', 'form', 'header'
        """
        parts = {
            "path": {},
            "query": {},
            "body": {},
            "form": {},
            "header": {},
        }
        
        for mapping in mappings:
            field_name = mapping.field_name
            param_location = mapping.param_location
            default_value = mapping.default_value
            
            # 获取参数值
            value = args.get(field_name)
            if value is None and default_value:
                value = default_value
            
            if value is not None and param_location in parts:
                parts[param_location][field_name] = value
        
        return parts


# 全局单例
mcp_tool_registry = McpToolRegistry()