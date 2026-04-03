# -*- coding: utf-8 -*-
"""
Chat Schemas - 对话相关的请求/响应模型
"""

from typing import Optional, List
from pydantic import BaseModel


class MicroserviceInfo(BaseModel):
    """微服务信息"""

    id: int
    name: str
    health_status: str


class GatewayVerifyResponse(BaseModel):
    """网关验证响应"""

    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str]
    microservices: List[MicroserviceInfo]


class SessionRequest(BaseModel):
    """WebSocket 会话请求"""

    gateway_key: str
    llm_key: str
    microservice_ids: Optional[List[int]] = None  # 可选：筛选微服务列表


class SessionResponse(BaseModel):
    """WebSocket 会话响应"""

    session_id: str
    websocket_url: str
    message: str
