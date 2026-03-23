# -*- coding: utf-8 -*-
"""
Tool Schemas - 工具相关的请求/响应模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolStatusInfo(BaseModel):
    """工具状态信息"""
    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    http_url: str
    error: Optional[str] = None


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[ToolInfo]
    total: int


class ToolStatusResponse(BaseModel):
    """工具状态响应"""
    tools: List[ToolStatusInfo]
    total: int
