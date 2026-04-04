# -*- coding: utf-8 -*-
"""
LLM Config Schemas - LLM配置相关请求/响应模型
从 gateway.py 路由中提取
"""

from typing import Optional, List
from pydantic import BaseModel


class LlmConfigCreate(BaseModel):
    config_name: str
    api_type: str  # openai/anthropic
    base_url: str
    model_name: str
    api_key: str  # 明文API Key，后端加密存储
    description: Optional[str] = None


class LlmConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    api_type: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None  # 如果提供新的Key，会加密存储
    description: Optional[str] = None
    status: Optional[int] = None


class GatewayLlmBind(BaseModel):
    llm_config_ids: List[str]


class LlmConfigBindRequest(BaseModel):
    llm_config_id: str
