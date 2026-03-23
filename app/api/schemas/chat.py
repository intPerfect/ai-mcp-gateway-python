# -*- coding: utf-8 -*-
"""
Chat Schemas - 对话相关的请求/响应模型
"""
from typing import Optional, List
from pydantic import BaseModel


class SessionRequest(BaseModel):
    """WebSocket 会话请求"""
    gateway_key: str
    llm_key: str
    microservice_ids: Optional[List[int]] = None  # 可选：筛选微服务


class SessionResponse(BaseModel):
    """WebSocket 会话响应"""
    session_id: str
    websocket_url: str
    message: str
