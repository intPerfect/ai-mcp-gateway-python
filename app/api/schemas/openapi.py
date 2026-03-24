# -*- coding: utf-8 -*-
"""
OpenAPI Schemas - OpenAPI导入相关的请求/响应模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class OpenAPIImportRequest(BaseModel):
    """OpenAPI导入请求"""
    gateway_id: str = "gateway_001"
    service_name: str
    service_url: str
    openapi_url: Optional[str] = None
    openapi_spec: Optional[Dict] = None
    microservice_id: Optional[int] = None  # 绑定到微服务


class ParameterInfo(BaseModel):
    """参数信息"""
    name: str
    param_in: str  # path, query, header, body, form, file
    type: str
    required: bool
    description: str
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    example: Optional[Any] = None


class OpenAPIToolInfo(BaseModel):
    """解析后的工具信息"""
    name: str
    description: str
    method: str
    path: str
    parameters: List[Dict]


class OpenAPIPreviewResponse(BaseModel):
    """OpenAPI预览响应"""
    total: int
    tools: List[OpenAPIToolInfo]


class OpenAPIImportResponse(BaseModel):
    """OpenAPI导入响应"""
    message: str
    tools: List[Dict[str, Any]]
