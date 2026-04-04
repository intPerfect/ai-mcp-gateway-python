# -*- coding: utf-8 -*-
"""
MCP Tool Registry v3.0 - 动态工具注册服务
从数据库读取接口配置，健康检查后动态注册MCP工具
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import async_session_factory
from app.infrastructure.database.repositories import ToolRepository, MicroserviceRepository

logger = logging.getLogger(__name__)

# 调用状态常量
CALL_STATUS_SUNNY = "sunny"    # 晴朗 - 错误率 < 10%
CALL_STATUS_CLOUDY = "cloudy"  # 阴云 - 错误率 10%-50%
CALL_STATUS_RAINY = "rainy"    # 下雨 - 错误率 > 50%

# 错误率阈值
ERROR_RATE_SUNNY_THRESHOLD = 0.10   # 低于10%为晴朗
ERROR_RATE_CLOUDY_THRESHOLD = 0.50  # 低于50%为阴云，高于50%为下雨
MIN_CALL_COUNT = 5  # 最少调用次数才开始计算状态


def calculate_status_by_error_rate(call_count: int, error_count: int) -> str:
    """
    根据错误率计算调用状态
    
    规则:
    - 调用次数 < 5: 默认晴朗（样本不足）
    - 错误率 < 10%: 晴朗
    - 错误率 10%-50%: 阴云
    - 错误率 > 50%: 下雨
    """
    if call_count < MIN_CALL_COUNT:
        return CALL_STATUS_SUNNY
    
    error_rate = error_count / call_count
    
    if error_rate < ERROR_RATE_SUNNY_THRESHOLD:
        return CALL_STATUS_SUNNY
    elif error_rate < ERROR_RATE_CLOUDY_THRESHOLD:
        return CALL_STATUS_CLOUDY
    else:
        return CALL_STATUS_RAINY


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
        self._repository: Optional[ToolRepository] = None
    
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
    
    def get_tool_definitions_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取按微服务分组的工具定义列表"""
        # 从工具状态中获取微服务信息
        # 这里需要从数据库获取工具的微服务关联信息
        return {"_all": self.get_tool_definitions()}
    
    def get_tool_definitions_by_microservice(
        self, 
        microservice_ids: List[int],
        db_session: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        根据微服务ID列表过滤工具定义
        
        Args:
            microservice_ids: 微服务ID列表，空列表表示获取所有工具
            db_session: 数据库会话（用于获取工具-微服务关联）
        
        Returns:
            工具定义列表
        """
        if not microservice_ids:
            return self.get_tool_definitions()
        
        # 如果没有数据库会话，返回所有工具
        if not db_session:
            return self.get_tool_definitions()
        
        # 异步方法需要在外部处理
        return self.get_tool_definitions()
    
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
        gateway_id: str = None,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """从数据库加载工具配置，如果 gateway_id 为 None 则加载所有工具
        
        Args:
            db_session: 数据库会话
            gateway_id: 网关ID，None 表示加载所有工具
            force_reload: 是否强制重新加载（会清空现有工具）
        """
        self._repository = ToolRepository(db_session)
        
        # 强制重新加载时清空现有工具
        if force_reload:
            self._tools.clear()
            self._tool_status.clear()
        
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
                    mappings=mappings,
                    tool_id=tool.tool_id
                )
                
                if self.register_tool(
                    name=tool.tool_name,
                    description=tool.tool_description,
                    input_schema=input_schema,
                    handler=handler
                ):
                    result["registered"].append(tool.tool_name)
                else:
                    # 工具已存在，跳过（静默处理，支持增量加载）
                    pass
                    
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
        
        包含所有参数（path参数用于替换URL模板中的占位符）
        """
        if not mappings:
            return {"type": "object", "properties": {}, "required": []}
        
        # 不过滤path参数，LLM需要知道所有需要传递的参数
        input_mappings = mappings
        
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
    
    async def _update_tool_status_independent(
        self,
        tool_id: int,
        call_code: str = None,
        is_error: bool = False
    ) -> None:
        """
        使用独立的数据库session更新工具调用状态
        这样可以避免多个并发工具调用共享同一个session导致的阻塞问题
        """
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    repo = ToolRepository(session)
                    # 先获取当前状态
                    tool = await repo.get_tool_by_id(tool_id)
                    if not tool:
                        return
                        
                    current_call_count = tool.call_count or 0
                    current_error_count = tool.error_count or 0
                        
                    new_call_count = current_call_count + 1
                    new_error_count = current_error_count + (1 if is_error else 0)
                    new_call_status = calculate_status_by_error_rate(new_call_count, new_error_count)
                        
                    await repo.update_tool_call_status(
                        tool_id=tool_id,
                        call_status=new_call_status,
                        call_code=call_code,
                        is_error=is_error
                    )
        except Exception as e:
            logger.warning(f"更新工具调用状态失败: {tool_id} - {str(e)}")
    
    def _create_http_handler(
        self,
        http_url: str,
        http_method: str,
        http_headers: Dict[str, str],
        timeout: int,
        mappings: List,
        tool_id: int = None
    ) -> Callable:
        """
        创建HTTP调用handler
            
        支持多种参数位置：path/query/body/form/header
        """
            
        async def handler(args: Dict[str, Any]) -> Any:
            try:
                # 直接执行HTTP请求，不再预先查询数据库
                async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                    # 根据mappings构建请求数据
                    request_parts = self._build_request_parts(mappings, args)
                    
                    # 调试日志：显示参数映射结果
                    logger.info(f"[工具调用] handler收到参数: {args}")
                    logger.info(f"[工具调用] mappings数量: {len(mappings) if mappings else 0}")
                    logger.info(f"[工具调用] request_parts: {request_parts}")
                        
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
                    
                    # 调试日志：显示最终请求信息
                    logger.info(f"[工具调用] 最终URL: {final_url}")
                    logger.info(f"[工具调用] HTTP方法: {http_method.upper()}")
                    logger.info(f"[工具调用] 查询参数: {query_params}")
                    logger.info(f"[工具调用] 请求体: {body_data}")
                    
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
                        # 对于 POST/PUT/PATCH 等请求，也需要传递 query_params
                        response = await client.request(
                            method=http_method,
                            url=final_url,
                            json=body_data if body_data else None,
                            params=query_params if query_params else None,
                            headers=final_headers
                        )
                        
                    # 解析响应
                    response_data = None
                    try:
                        response_data = response.json()
                    except:
                        response_data = {"data": response.text}
                        
                    # 判断本次调用是否为错误
                    is_error = False
                    call_code = str(response.status_code)
                        
                    if response.status_code >= 400:
                        # HTTP错误
                        is_error = True
                    elif response_data and isinstance(response_data, dict):
                        # 检查业务code
                        biz_code = response_data.get("code")
                        if biz_code and biz_code != "0000":
                            is_error = True
                            call_code = str(biz_code)
                        
                    # 使用独立session异步更新调用状态（不阻塞HTTP响应返回）
                    if tool_id:
                        asyncio.create_task(
                            self._update_tool_status_independent(
                                tool_id=tool_id,
                                call_code=call_code,
                                is_error=is_error
                            )
                        )
                        
                    if response.status_code < 400:
                        return response_data
                    else:
                        return {"error": f"HTTP {response.status_code}: {response.text}", **response_data}
                            
            except httpx.TimeoutException:
                # 使用独立session异步更新错误状态
                if tool_id:
                    asyncio.create_task(
                        self._update_tool_status_independent(
                            tool_id=tool_id,
                            call_code="TIMEOUT",
                            is_error=True
                        )
                    )
                return {"error": "请求超时"}
            except httpx.ConnectError:
                # 使用独立session异步更新错误状态
                if tool_id:
                    asyncio.create_task(
                        self._update_tool_status_independent(
                            tool_id=tool_id,
                            call_code="CONNECT_ERROR",
                            is_error=True
                        )
                    )
                return {"error": f"连接失败: {http_url}"}
            except Exception as e:
                # 使用独立session异步更新错误状态
                if tool_id:
                    asyncio.create_task(
                        self._update_tool_status_independent(
                            tool_id=tool_id,
                            call_code="EXCEPTION",
                            is_error=True
                        )
                    )
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

    async def get_tools_with_microservice(
        self, microservice_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取带 microservice_name 的工具列表

        Args:
            microservice_ids: 可选，筛选指定微服务的工具。为 None 时返回所有工具
        """
        async with async_session_factory() as session:
            tool_repo = ToolRepository(session)
            ms_repo = MicroserviceRepository(session)
            all_tools = await tool_repo.get_all_tools()
            enabled_tools = [t for t in all_tools if t.enabled == 1]
            all_microservices = await ms_repo.get_all_microservices()
            ms_map = {ms.id: ms.name for ms in all_microservices}

            result = []
            for tool in enabled_tools:
                # 过滤：必须有微服务绑定
                if not tool.microservice_id or tool.microservice_id not in ms_map:
                    continue

                # 如果指定了微服务筛选，只返回选中微服务的工具
                if microservice_ids and tool.microservice_id not in microservice_ids:
                    continue

                tool_def = self.get_tool(tool.tool_name)
                if tool_def:
                    result.append(
                        {
                            "name": tool_def.name,
                            "description": tool_def.description,
                            "input_schema": tool_def.input_schema,
                            "microservice_name": ms_map[tool.microservice_id],
                        }
                    )

            logger.info(f"加载工具: {len(result)} 个, 筛选微服务: {microservice_ids}")
            return result


# 全局单例
mcp_tool_registry = McpToolRegistry()