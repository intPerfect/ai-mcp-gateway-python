# -*- coding: utf-8 -*-
"""
LLM Service - 兼容导入层
实际实现已拆分到 app/services/llm/ 子模块
"""

from app.services.llm.base import LLMService  # noqa: F401

# 全局单例（默认配置）
llm_service = LLMService()
