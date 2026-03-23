# -*- coding: utf-8 -*-
"""
API Schemas - 请求/响应模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.api.schemas.chat import SessionRequest, SessionResponse
from app.api.schemas.tool import ToolInfo, ToolStatusInfo
from app.api.schemas.openapi import OpenAPIImportRequest, OpenAPIToolInfo


class Response(BaseModel):
    """Generic API response"""
    code: str = "0000"
    info: str = "success"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response"""
    code: str
    info: str


class JSONRPCRequest(BaseModel):
    """JSON-RPC request model"""
    jsonrpc: str = "2.0"
    method: str
    id: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC error"""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC response model"""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


class ServerInfo(BaseModel):
    """MCP Server information"""
    name: str
    version: str


class Capabilities(BaseModel):
    """MCP Server capabilities"""
    tools: Optional[Dict[str, bool]] = None
    resources: Optional[Dict[str, bool]] = None


class InitializeResult(BaseModel):
    """MCP Initialize result"""
    protocolVersion: str
    capabilities: Capabilities
    serverInfo: ServerInfo


class ToolInputSchema(BaseModel):
    """Tool input schema"""
    type: str = "object"
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None
    additionalProperties: bool = False


class Tool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: ToolInputSchema


class ToolsListResult(BaseModel):
    """Tools list result"""
    tools: List[Tool]


class ContentItem(BaseModel):
    """Tool call content item"""
    type: str = "text"
    text: str


class ToolCallResult(BaseModel):
    """Tool call result"""
    content: List[ContentItem]
    isError: bool = False


__all__ = [
    "SessionRequest", "SessionResponse",
    "ToolInfo", "ToolStatusInfo",
    "OpenAPIImportRequest", "OpenAPIToolInfo",
    "Response", "ErrorResponse",
    "JSONRPCRequest", "JSONRPCError", "JSONRPCResponse",
    "ServerInfo", "Capabilities", "InitializeResult",
    "ToolInputSchema", "Tool", "ToolsListResult",
    "ContentItem", "ToolCallResult"
]
