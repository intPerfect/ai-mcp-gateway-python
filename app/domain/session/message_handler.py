"""
MCP Message Handler - Handles JSON-RPC messages for MCP protocol
"""
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repository import McpGatewayRepository
from app.domain.session.models import (
    ToolConfig, 
    ProtocolMapping, 
    HttpConfig, 
    ToolProtocolConfig,
    GatewayConfig
)
from app.domain.protocol.http_gateway import HttpGateway
from app.utils.exceptions import MethodNotFoundException

logger = logging.getLogger(__name__)

# MCP Protocol constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

# MCP Error codes
class McpErrorCodes:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MessageHandler:
    """Handler for MCP JSON-RPC messages"""
    
    def __init__(self, session: AsyncSession):
        self.repository = McpGatewayRepository(session)
        self.http_gateway = HttpGateway()
    
    async def handle(self, gateway_id: str, message_body: str) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC message
        
        Args:
            gateway_id: Gateway identifier
            message_body: Raw JSON-RPC message
            
        Returns:
            JSON-RPC response
        """
        try:
            message = json.loads(message_body)
            method = message.get("method", "")
            msg_id = message.get("id")
            params = message.get("params", {})
            
            logger.info(f"Handling message: method={method}, id={msg_id}")
            
            # Route to appropriate handler
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
            logger.error(f"JSON parse error: {e}")
            return self._error_response(None, McpErrorCodes.PARSE_ERROR, str(e))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return self._error_response(
                message.get("id") if 'message' in dir() else None,
                McpErrorCodes.INTERNAL_ERROR,
                str(e)
            )
    
    async def _handle_initialize(self, gateway_id: str, msg_id: Any, params: Dict) -> Dict:
        """Handle initialize request"""
        # Get gateway config
        gateway = await self.repository.get_gateway_by_id(gateway_id)
        
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
        """Handle initialized notification"""
        # This is a notification, no response needed but we return empty for consistency
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {}
        }
    
    async def _handle_ping(self, msg_id: Any) -> Dict:
        """Handle ping request"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {}
        }
    
    async def _handle_tools_list(self, gateway_id: str, msg_id: Any, params: Dict) -> Dict:
        """Handle tools/list request - Return list of available tools"""
        tools = await self.repository.get_tools_by_gateway_id(gateway_id)
        
        tool_list = []
        for tool in tools:
            # Get protocol mappings
            mappings = await self.repository.get_protocol_mappings(tool.protocol_id, "request")
            
            # Build input schema
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
        """Handle tools/call request - Execute a tool"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return self._error_response(msg_id, McpErrorCodes.INVALID_PARAMS, "Tool name is required")
            
            # Get tool configuration
            tool = await self.repository.get_tool_by_name(gateway_id, tool_name)
            if not tool:
                return self._error_response(msg_id, McpErrorCodes.METHOD_NOT_FOUND, f"Tool not found: {tool_name}")
            
            # Get HTTP protocol config
            http_protocol = await self.repository.get_protocol_http_by_id(tool.protocol_id)
            if not http_protocol:
                return self._error_response(msg_id, McpErrorCodes.INTERNAL_ERROR, "Protocol configuration not found")
            
            http_config = HttpConfig(
                http_url=http_protocol.http_url,
                http_method=http_protocol.http_method,
                http_headers=http_protocol.http_headers,
                timeout=http_protocol.timeout
            )
            
            # Call the tool
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
            logger.error(f"Error calling tool: {e}", exc_info=True)
            return self._error_response(msg_id, McpErrorCodes.INVALID_PARAMS, str(e))
    
    async def _handle_resources_list(self, msg_id: Any, params: Dict) -> Dict:
        """Handle resources/list request"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {
                "resources": []
            }
        }
    
    def _build_input_schema(self, mappings: List) -> Dict:
        """Build JSON Schema from protocol mappings"""
        if not mappings:
            return {"type": "object", "properties": {}, "required": []}
        
        # Sort by sort_order
        sorted_mappings = sorted(mappings, key=lambda x: x.sort_order or 0)
        
        # Build parent-children map
        children_map: Dict[str, List] = {}
        roots = []
        
        for mapping in sorted_mappings:
            if mapping.parent_path is None:
                roots.append(mapping)
            else:
                if mapping.parent_path not in children_map:
                    children_map[mapping.parent_path] = []
                children_map[mapping.parent_path].append(mapping)
        
        # Build schema
        properties = {}
        required = []
        
        for root in roots:
            properties[root.field_name] = self._build_property(root, children_map)
            if root.is_required == 1:
                required.append(root.field_name)
        
        # Determine type
        schema_type = roots[0].mcp_type if len(roots) == 1 else "object"
        
        return {
            "type": schema_type,
            "properties": properties,
            "required": required if required else None,
            "additionalProperties": False
        }
    
    def _build_property(self, mapping, children_map: Dict) -> Dict:
        """Build property schema recursively"""
        prop = {
            "type": mapping.mcp_type
        }
        
        if mapping.mcp_desc:
            prop["description"] = mapping.mcp_desc
        
        # Check for children
        children = children_map.get(mapping.mcp_path, [])
        if children:
            # Sort children
            children = sorted(children, key=lambda x: x.sort_order or 0)
            
            props = {}
            reqs = []
            
            for child in children:
                props[child.field_name] = self._build_property(child, children_map)
                if child.is_required == 1:
                    reqs.append(child.field_name)
            
            prop["properties"] = props
            if reqs:
                prop["required"] = reqs
        
        return prop
    
    def _error_response(self, msg_id: Any, code: int, message: str) -> Dict:
        """Create error response"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }
