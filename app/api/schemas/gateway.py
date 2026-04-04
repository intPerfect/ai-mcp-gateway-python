# -*- coding: utf-8 -*-
"""
Gateway Schemas - 网关相关请求/响应模型
从 gateway.py 路由中提取
"""

from typing import Optional
from pydantic import BaseModel


class GatewayCreate(BaseModel):
    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str] = None
    version: str = "1.0.0"
    auth: int = 0


class GatewayUpdate(BaseModel):
    gateway_name: Optional[str] = None
    gateway_desc: Optional[str] = None
    version: Optional[str] = None
    auth: Optional[int] = None
    status: Optional[int] = None


class GatewayKeyCreate(BaseModel):
    gateway_id: str
    rate_limit: int = 600
    expire_days: int = 365
    remark: Optional[str] = None


class GatewayMicroserviceBind(BaseModel):
    microservice_ids: list[int]
