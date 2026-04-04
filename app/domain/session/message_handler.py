"""
MCP Message Handler - Handles JSON-RPC messages for MCP protocol v3.0
"""
import json
import logging
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import GatewayRepository, ToolRepository
from app.domain.session.models import (
    HttpConfig
)
from app.domain.protocol.http_gateway import HttpGateway

logger = logging.getLogger(__name__)

# MCP Protocol constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


class McpErrorCodes:
    """MCP错误码"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MessageHandler:
    """MCP JSON-RPC消息处理器"""
    
    def __init__(self, session: AsyncSession):
        self.gateway_repo = GatewayRepository(session)
        self.tool_repo = ToolRepository(session)
        self.http_gateway = HttpGateway()
    
    async def handle(self, gateway_id: str, message_body: str) -> Dict[str, Any]:
        """处理JSON-RPC消息"""
        try:
            message = json.loads(message_body)
            method = message.get("method", "")
            msg_id = message.get("id")
            params = message.get("params", {})
            
            logger.info(f"处理消息: method={method}, id={msg_id}")
            
            # 路由到对应的处理器
            if method == "initialize":
                return await self._handle_initialize(gateway_id, msg_id, params)
            elif method == "notifications/initialized":
                return await self._handle_initialized(msg_id)
            elif method == "tools/list":
                return await self._handle_tools_list(gateway_id, msg_id, params)
            elif method == "tools/call":
                return await self._handle_tools_call(gateway_id, msg_id, params)
            elif method == "resources/list":
                return await self._handle_resources_list(msg_id, params)
            elif method == "ping":
                return await self._handle_ping(msg_id)
            else:
                return self._error_response(
                    msg_id, 
                    McpErrorCodes.METHOD_NOT_FOUND, 
                    f"Method not found: {method}"
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return self._error_response(None, McpErrorCodes.PARSE_ERROR, str(e))
        except Exception as e:
            logger.error(f"消息处理错误: {e}", exc_info=True)
            return self._error_response(
                message.get("id") if 'message' in dir() else None,
                McpErrorCodes.INTERNAL_ERROR,
                str(e)
            )
    
    async def _handle_initialize(self, gateway_id: str, msg_id: Any, params: Dict) -> Dict:
        """处理初始化请求"""
        gateway = await self.gateway_repo.get_gateway_by_id(gateway_id)
        
        server_name = "Python MCP Gateway"
        server_version = "1.0.0"
        
        if gateway:
            server_name = gateway.gateway_name
            server_version = gateway.version or "1.0.0"
        
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": False, "listChanged": False}
                },
                "serverInfo": {
                    "name": server_name,
                    "version": server_version
                }
            }
        }
    
    async def _handle_initialized(self, msg_id: Any) -> Dict:
        """处理初始化完成通知"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {}
        }
    
    async def _handle_ping(self, msg_id: Any) -> Dict:
        """处理ping请求"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {}
        }
    
    async def _handle_tools_list(self, gateway_id: str, msg_id: Any, params: Dict) -> Dict:
        """处理工具列表请求"""
        tools = await self.tool_repo.get_tools_by_gateway_id(gateway_id)
        
        tool_list = []
        for tool in tools:
            mappings = await self.tool_repo.get_protocol_mappings(tool.protocol_id)
            input_schema = self._build_input_schema(mappings)
            
            tool_list.append({
                "name": tool.tool_name,
                "description": tool.tool_description,
                "inputSchema": input_schema
            })
        
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {
                "tools": tool_list
            }
        }
    
    async def _handle_tools_call(self, gateway_id: str, msg_id: Any, params: Dict) -> Dict:
        """处理工具调用请求"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return self._error_response(msg_id, McpErrorCodes.INVALID_PARAMS, "Tool name is required")
            
            tool = await self.tool_repo.get_tool_by_name(gateway_id, tool_name)
            if not tool:
                return self._error_response(msg_id, McpErrorCodes.METHOD_NOT_FOUND, f"Tool not found: {tool_name}")
            
            http_protocol = await self.tool_repo.get_protocol_http_by_id(tool.protocol_id)
            if not http_protocol:
                return self._error_response(msg_id, McpErrorCodes.INTERNAL_ERROR, "Protocol configuration not found")
            
            http_config = HttpConfig(
                http_url=http_protocol.http_url,
                http_method=http_protocol.http_method,
                http_headers=http_protocol.http_headers,
                timeout=http_protocol.timeout
            )
            
            result = await self.http_gateway.call(http_config, arguments)
            
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ],
                    "isError": False
                }
            }
            
        except Exception as e:
            logger.error(f"工具调用错误: {e}", exc_info=True)
            return self._error_response(msg_id, McpErrorCodes.INVALID_PARAMS, str(e))
    
    async def _handle_resources_list(self, msg_id: Any, params: Dict) -> Dict:
        """处理资源列表请求"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {
                "resources": []
            }
        }
    
    def _build_input_schema(self, mappings: List) -> Dict:
        """
        构建JSON Schema
        
        param_location: path/query/body/form/header/file
        - 包含所有参数（path参数用于替换URL模板中的占位符）
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
            
            # 添加描述
            if mapping.field_desc:
                prop["description"] = mapping.field_desc
            
            # 添加枚举值
            if mapping.enum_values:
                try:
                    import json
                    enum_list = json.loads(mapping.enum_values)
                    prop["enum"] = enum_list
                except:
                    pass
            
            # 添加默认值
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
    
    def _error_response(self, msg_id: Any, code: int, message: str) -> Dict:
        """创建错误响应"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }