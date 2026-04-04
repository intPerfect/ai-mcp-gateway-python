# -*- coding: utf-8 -*-
"""
LLM Service Base - LLMService 公共接口
整合 Anthropic/OpenAI 两种 Provider
"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from app.config import get_settings
from app.services.mcp_tool_registry import mcp_tool_registry
from app.services.llm.message_converter import AnthropicMessageConverter
from app.services.llm.openai_provider import (
    convert_to_openai_messages,
    chat_openai,
    chat_stream_openai,
)
from app.services.llm.anthropic_provider import (
    chat_anthropic,
    chat_stream_anthropic,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """LLM服务 - 支持OpenAI和Anthropic两种API类型"""

    def __init__(
        self,
        api_type: str = "anthropic",
        base_url: str = None,
        model_name: str = None,
        api_key: str = None,
    ):
        self.api_type = api_type.lower()
        self.base_url = base_url or settings.llm_api_base_url
        self.model = model_name or settings.llm_model
        self.api_key = api_key

    def get_tools(
        self, allowed_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取工具定义，可按名称筛选"""
        all_tools = mcp_tool_registry.get_tool_definitions()
        if allowed_names is not None:
            return [t for t in all_tools if t.get("name") in allowed_names]
        return all_tools

    def _convert_to_anthropic_messages(
        self, messages: List[Dict[str, Any]]
    ) -> tuple:
        """转换消息为 Anthropic API 格式"""
        return AnthropicMessageConverter.convert(messages)

    def _convert_to_openai_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """转换消息为 OpenAI API 格式"""
        return convert_to_openai_messages(messages)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool = True,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用LLM API"""
        effective_api_key = api_key or self.api_key or settings.llm_api_key
        if not effective_api_key:
            return {
                "error": "LLM API Key未配置",
                "tool_calls": [],
                "content_blocks": [],
            }

        tools = self.get_tools() if tools_enabled else None

        if self.api_type == "openai":
            openai_messages = self._convert_to_openai_messages(messages)
            return await chat_openai(
                base_url=self.base_url,
                model=self.model,
                messages=messages,
                openai_messages=openai_messages,
                tools=tools,
                tools_enabled=tools_enabled,
                api_key=effective_api_key,
            )
        else:
            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(
                messages
            )
            return await chat_anthropic(
                base_url=self.base_url,
                model=self.model,
                messages=messages,
                system_prompt=system_prompt,
                anthropic_messages=anthropic_messages,
                tools=tools,
                tools_enabled=tools_enabled,
                api_key=effective_api_key,
            )

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具（委托给mcp_tool_registry）"""
        return await mcp_tool_registry.execute_tool(tool_name, arguments)

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool = True,
        api_key: Optional[str] = None,
        allowed_names: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用LLM API"""
        effective_api_key = api_key or self.api_key or settings.llm_api_key
        if not effective_api_key:
            yield {"type": "error", "error": "LLM API Key未配置"}
            return

        tools = self.get_tools(allowed_names=allowed_names) if tools_enabled else None

        if self.api_type == "openai":
            openai_messages = self._convert_to_openai_messages(messages)
            async for event in chat_stream_openai(
                base_url=self.base_url,
                model=self.model,
                openai_messages=openai_messages,
                tools=tools,
                tools_enabled=tools_enabled,
                api_key=effective_api_key,
            ):
                yield event
        else:
            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(
                messages
            )
            async for event in chat_stream_anthropic(
                base_url=self.base_url,
                model=self.model,
                system_prompt=system_prompt,
                anthropic_messages=anthropic_messages,
                tools=tools,
                tools_enabled=tools_enabled,
                api_key=effective_api_key,
            ):
                yield event
