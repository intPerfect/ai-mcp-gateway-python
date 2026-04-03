# -*- coding: utf-8 -*-
"""
Microservice Schemas - 微服务相关的请求/响应模型
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class MicroserviceCreate(BaseModel):
    """创建微服务请求"""
    name: str
    http_base_url: str
    description: Optional[str] = None
    business_line_id: Optional[int] = None


class MicroserviceUpdate(BaseModel):
    """更新微服务请求"""
    name: Optional[str] = None
    http_base_url: Optional[str] = None
    description: Optional[str] = None
    business_line_id: Optional[int] = None
    status: Optional[int] = None


class MicroserviceResponse(BaseModel):
    """微服务响应"""
    id: int
    name: str
    http_base_url: str
    description: Optional[str] = None
    business_line_id: Optional[int] = None
    business_line: Optional[str] = None
    health_status: str = "unknown"
    last_check_time: Optional[datetime] = None
    status: int = 1
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ToolBindRequest(BaseModel):
    """工具绑定请求"""
    microservice_id: int


class ToolEnabledRequest(BaseModel):
    """工具启用状态更新请求"""
    enabled: int  # 0-禁用 1-启用


class ToolResponse(BaseModel):
    """工具响应（包含微服务信息）"""
    id: int
    tool_id: int
    tool_name: str
    tool_description: str
    microservice_id: Optional[int] = None
    microservice_name: Optional[str] = None
    enabled: int = 1
    call_status: str = "sunny"
    last_call_time: Optional[datetime] = None
    last_call_code: Optional[str] = None
    call_count: int = 0
    error_count: int = 0

    class Config:
        from_attributes = True
