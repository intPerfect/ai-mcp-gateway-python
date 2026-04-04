# -*- coding: utf-8 -*-
"""
LLM Service - 大模型调用服务 (支持OpenAI和Anthropic兼容)
"""

import json
import logging
import asyncio
import secrets
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
from openai import OpenAI
from app.config import get_settings
from app.services.mcp_tool_registry import mcp_tool_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """LLM服务 - 支持OpenAI和Anthropic两种API类型"""

    def __init__(
        self,
        api_type: str = "anthropic",
        base_url: str = None,
        model_name: str = None,
        api_key: str = None
    ):
        """
        初始化LLM服务

        Args:
            api_type: API类型 (openai/anthropic)
            base_url: API基础URL
            model_name: 模型名称
            api_key: API Key
        """
        self.api_type = api_type.lower()
        self.base_url = base_url or settings.llm_api_base_url
        self.model = model_name or settings.llm_model
        self.api_key = api_key

    def get_tools(self, allowed_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取工具定义，可按名称筛选"""
        all_tools = mcp_tool_registry.get_tool_definitions()
        if allowed_names is not None:
            return [t for t in all_tools if t.get('name') in allowed_names]
        return all_tools

    def _convert_to_anthropic_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> tuple:
        """
        转换消息为 Anthropic API 格式

        Args:
            messages: 原始消息列表

        Returns:
            Tuple[str, List]: (system_prompt, anthropic_messages)
        """
        anthropic_messages = []
        system_prompt = ""

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = (
                    content if isinstance(content, str) else str(content)
                )
            elif role == "user":
                if isinstance(content, str):
                    anthropic_messages.append(
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": content}],
                        }
                    )
                else:
                    anthropic_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                if isinstance(content, str):
                    anthropic_messages.append(
                        {
                            "role": "assistant",
                            "content": [{"type": "text", "text": content}],
                        }
                    )
                else:
                    assistant_content = []
                    tool_result_content = []
                    for block in content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                            if block_type == "thinking":
                                assistant_content.append(
                                    {
                                        "type": "thinking",
                                        "thinking": block.get("thinking", ""),
                                    }
                                )
                            elif block_type == "text":
                                assistant_content.append(
                                    {"type": "text", "text": block.get("text", "")}
                                )
                            elif block_type == "tool_use":
                                assistant_content.append(
                                    {
                                        "type": "tool_use",
                                        "id": block.get("id", ""),
                                        "name": block.get("name", ""),
                                        "input": block.get("input", {}),
                                    }
                                )
                            elif block_type == "tool_result":
                                tool_result_content.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.get("tool_use_id", ""),
                                        "content": block.get("content", ""),
                                    }
                                )
                    if assistant_content:
                        anthropic_messages.append(
                            {"role": "assistant", "content": assistant_content}
                        )
                    if tool_result_content:
                        anthropic_messages.append(
                            {"role": "user", "content": tool_result_content}
                        )

        return system_prompt, anthropic_messages

    def _convert_to_openai_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        转换消息为 OpenAI API 格式

        Args:
            messages: 原始消息列表

        Returns:
            List: openai_messages
        """
        openai_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                openai_messages.append({"role": "system", "content": content})
            elif role == "user":
                if isinstance(content, str):
                    openai_messages.append({"role": "user", "content": content})
                else:
                    # 处理多模态内容
                    openai_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                if isinstance(content, str):
                    openai_messages.append({"role": "assistant", "content": content})
                else:
                    # 处理工具调用等内容
                    assistant_msg = {"role": "assistant", "content": ""}
                    tool_calls = []
                    for block in content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                            if block_type == "text":
                                assistant_msg["content"] = block.get("text", "")
                            elif block_type == "tool_use":
                                tool_calls.append({
                                    "id": block.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name", ""),
                                        "arguments": json.dumps(block.get("input", {}))
                                    }
                                })
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    openai_messages.append(assistant_msg)

        return openai_messages

    def _convert_tools_to_openai_format(self, tools: List[Dict]) -> List[Dict]:
        """将Anthropic格式的工具转换为OpenAI格式"""
        openai_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                })
        return openai_tools

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

        if self.api_type == "openai":
            return await self._chat_openai(messages, tools_enabled, effective_api_key)
        else:
            return await self._chat_anthropic(messages, tools_enabled, effective_api_key)

    async def _chat_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool,
        api_key: str
    ) -> Dict[str, Any]:
        """调用Anthropic API"""
        try:
            client = anthropic.Anthropic(
                base_url=self.base_url,
                api_key=api_key,
            )

            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(messages)

            request_kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": anthropic_messages,
                "temperature": 1.0,
            }

            if system_prompt:
                request_kwargs["system"] = system_prompt

            if tools_enabled:
                request_kwargs["tools"] = self.get_tools()

            response = await asyncio.to_thread(client.messages.create, **request_kwargs)

            result_content = ""
            result_content_blocks = []
            tool_calls = []

            for block in response.content:
                block_dict = {"type": block.type}
                if block.type == "text":
                    block_dict["text"] = block.text
                    result_content = block.text
                elif block.type == "tool_use":
                    block_dict["id"] = block.id
                    block_dict["name"] = block.name
                    block_dict["input"] = block.input
                    tool_calls.append(
                        {"id": block.id, "name": block.name, "input": block.input}
                    )
                elif block.type == "thinking":
                    block_dict["thinking"] = getattr(block, "thinking", "")

                result_content_blocks.append(block_dict)

            return {
                "content": result_content,
                "content_blocks": result_content_blocks,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"Anthropic API调用异常: {str(e)}")
            return {
                "content": f"LLM调用异常: {str(e)}",
                "error": str(e),
                "tool_calls": [],
                "content_blocks": [],
            }

    async def _chat_openai(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool,
        api_key: str
    ) -> Dict[str, Any]:
        """调用OpenAI兼容API"""
        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=api_key,
            )

            openai_messages = self._convert_to_openai_messages(messages)

            request_kwargs = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": 1.0,
            }

            if tools_enabled:
                tools = self.get_tools()
                if tools:
                    request_kwargs["tools"] = self._convert_tools_to_openai_format(tools)

            response = await asyncio.to_thread(client.chat.completions.create, **request_kwargs)

            result_content = ""
            result_content_blocks = []
            tool_calls = []

            choice = response.choices[0]
            message = choice.message

            if message.content:
                result_content = message.content
                result_content_blocks.append({"type": "text", "text": message.content})

            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments) if tc.function.arguments else {}
                    })
                    result_content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments) if tc.function.arguments else {}
                    })

            return {
                "content": result_content,
                "content_blocks": result_content_blocks,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"OpenAI API调用异常: {str(e)}")
            return {
                "content": f"LLM调用异常: {str(e)}",
                "error": str(e),
                "tool_calls": [],
                "content_blocks": [],
            }

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

        if self.api_type == "openai":
            async for event in self._chat_stream_openai(messages, tools_enabled, effective_api_key, allowed_names):
                yield event
        else:
            async for event in self._chat_stream_anthropic(messages, tools_enabled, effective_api_key, allowed_names):
                yield event

    async def _chat_stream_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool,
        api_key: str,
        allowed_names: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用Anthropic API"""
        try:
            client = anthropic.Anthropic(
                base_url=self.base_url,
                api_key=api_key,
            )

            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(messages)

            request_kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": anthropic_messages,
                "temperature": 1.0,
            }
            if system_prompt:
                request_kwargs["system"] = system_prompt
            if tools_enabled:
                tools = self.get_tools(allowed_names=allowed_names)
                request_kwargs["tools"] = tools
                tool_names = [t.get('name') for t in tools]
                logger.info(f"启用工具调用，发送 {len(tools)} 个工具: {', '.join(tool_names)}")
            else:
                logger.info("工具调用已禁用")

            import queue
            import threading

            result_queue: queue.Queue = queue.Queue()

            def run_stream():
                try:
                    with client.messages.stream(**request_kwargs) as stream:
                        for event in stream:
                            result_queue.put(("event", event))
                        result_queue.put(("final", stream.get_final_message()))
                except Exception as e:
                    result_queue.put(("error", e))
                finally:
                    result_queue.put(("done", None))

            threading.Thread(target=run_stream, daemon=True).start()

            loop = asyncio.get_event_loop()
            current_block_type = None
            accumulated_text = ""
            text_block_yielded_len = 0
            tool_calls = []
            content_blocks = []
            final_message = None

            while True:
                try:
                    kind, payload = await loop.run_in_executor(
                        None, lambda: result_queue.get(timeout=60)
                    )
                except Exception:
                    yield {"type": "error", "error": "Stream timeout"}
                    return

                if kind == "done":
                    break
                elif kind == "error":
                    yield {"type": "error", "error": str(payload)}
                    return
                elif kind == "final":
                    final_message = payload
                elif kind == "event":
                    event = payload
                    event_type = getattr(event, "type", None)

                    if event_type == "message_start":
                        yield {"type": "stream_start"}

                    elif event_type == "content_block_start":
                        content_block = getattr(event, "content_block", None)
                        if content_block:
                            current_block_type = getattr(content_block, "type", None)
                            if current_block_type == "text":
                                accumulated_text = ""
                                text_block_yielded_len = 0
                            elif current_block_type == "thinking":
                                logger.info("[LLM Event] content_block_start - thinking block started")
                            elif current_block_type == "tool_use":
                                yield {
                                    "type": "tool_use_start",
                                    "id": getattr(content_block, "id", ""),
                                    "name": getattr(content_block, "name", ""),
                                }

                    elif event_type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if delta:
                            delta_type = getattr(delta, "type", None)
                            if delta_type == "text_delta":
                                text = getattr(delta, "text", "")
                                accumulated_text += text
                                if "<minimax:tool_call>" not in accumulated_text:
                                    xml_start_idx = accumulated_text.find("<minimax")
                                    if xml_start_idx == -1:
                                        unsent = accumulated_text[text_block_yielded_len:]
                                        if unsent:
                                            yield {"type": "text_delta", "text": unsent}
                                            text_block_yielded_len = len(accumulated_text)
                                    else:
                                        safe_text = accumulated_text[text_block_yielded_len:xml_start_idx]
                                        if safe_text:
                                            yield {"type": "text_delta", "text": safe_text}
                                            text_block_yielded_len = xml_start_idx
                            elif delta_type == "thinking_delta":
                                thinking_text = getattr(delta, "thinking", "")
                                yield {
                                    "type": "thinking_delta",
                                    "thinking": thinking_text,
                                }

                    elif event_type == "content_block_stop":
                        if current_block_type == "text":
                            clean_text, xml_tool_calls = self._parse_minimax_tool_calls(accumulated_text)
                            if xml_tool_calls:
                                for tc in xml_tool_calls:
                                    tool_calls.append(tc)
                                    content_blocks.append(
                                        {
                                            "type": "tool_use",
                                            "id": tc["id"],
                                            "name": tc["name"],
                                            "input": tc["input"],
                                        }
                                    )
                                    yield {
                                        "type": "tool_use_start",
                                        "id": tc["id"],
                                        "name": tc["name"],
                                    }
                                    yield {"type": "tool_use_stop"}
                                if clean_text:
                                    content_blocks.append({"type": "text", "text": clean_text})
                                    yield {"type": "text_stop", "text": clean_text}
                                else:
                                    yield {"type": "text_stop", "text": ""}
                            else:
                                remaining = accumulated_text[text_block_yielded_len:]
                                if remaining:
                                    yield {"type": "text_delta", "text": remaining}
                                    text_block_yielded_len = len(accumulated_text)
                                content_blocks.append({"type": "text", "text": accumulated_text})
                                yield {"type": "text_stop", "text": accumulated_text}
                        elif current_block_type == "tool_use":
                            yield {"type": "tool_use_stop"}

            if final_message:
                logger.info(f"流结束，最终消息包含 {len(final_message.content)} 个内容块")
                content_blocks = []
                tool_calls = []
                
                for block in final_message.content:
                    block_type = block.type
                    if block_type == "tool_use":
                        tool_calls.append(
                            {"id": block.id, "name": block.name, "input": block.input}
                        )
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )
                    elif block_type == "text":
                        text_content = getattr(block, "text", "")
                        content_blocks.append({"type": "text", "text": text_content})
                        if text_content:
                            accumulated_text = text_content
                    elif block_type == "thinking":
                        thinking_content = getattr(block, "thinking", "")
                        content_blocks.append({"type": "thinking", "thinking": thinking_content})

            if accumulated_text and text_block_yielded_len < len(accumulated_text):
                remaining_text = accumulated_text[text_block_yielded_len:]
                if remaining_text:
                    yield {"type": "text_delta", "text": remaining_text}
            
            yield {
                "type": "stream_end",
                "content": accumulated_text,
                "content_blocks": content_blocks,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"Anthropic流式调用异常: {str(e)}")
            yield {"type": "error", "error": str(e)}

    async def _chat_stream_openai(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool,
        api_key: str,
        allowed_names: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用OpenAI兼容API"""
        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=api_key,
            )

            openai_messages = self._convert_to_openai_messages(messages)

            request_kwargs = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": 1.0,
                "stream": True,
            }

            if tools_enabled:
                tools = self.get_tools(allowed_names=allowed_names)
                if tools:
                    request_kwargs["tools"] = self._convert_tools_to_openai_format(tools)
                    logger.info(f"启用工具调用，发送 {len(tools)} 个工具")

            accumulated_text = ""
            tool_calls = []
            content_blocks = []
            current_tool_call = None

            yield {"type": "stream_start"}

            stream = await asyncio.to_thread(
                lambda: client.chat.completions.create(**request_kwargs)
            )

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta:
                    if delta.content:
                        accumulated_text += delta.content
                        yield {"type": "text_delta", "text": delta.content}

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index is not None:
                                while len(tool_calls) <= tc.index:
                                    tool_calls.append({"id": "", "name": "", "input": ""})
                                
                                if tc.id:
                                    tool_calls[tc.index]["id"] = tc.id
                                if tc.function and tc.function.name:
                                    tool_calls[tc.index]["name"] = tc.function.name
                                if tc.function and tc.function.arguments:
                                    tool_calls[tc.index]["input"] += tc.function.arguments

            # 处理工具调用
            for i, tc in enumerate(tool_calls):
                if tc["name"]:
                    try:
                        tc["input"] = json.loads(tc["input"]) if tc["input"] else {}
                    except:
                        tc["input"] = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"]
                    })
                    yield {
                        "type": "tool_use_start",
                        "id": tc["id"],
                        "name": tc["name"]
                    }
                    yield {"type": "tool_use_stop"}

            if accumulated_text:
                content_blocks.append({"type": "text", "text": accumulated_text})

            yield {
                "type": "stream_end",
                "content": accumulated_text,
                "content_blocks": content_blocks,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"OpenAI流式调用异常: {str(e)}")
            yield {"type": "error", "error": str(e)}

    def _parse_minimax_tool_calls(self, text: str):
        """
        解析 MiniMax 返回的 XML 格式工具调用
        格式: <minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>
        返回: (clean_text, tool_calls)
        """
        import re

        tool_calls = []
        clean_text = text

        pattern = r"<minimax:tool_call>(.*?)</minimax:tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                name_match = re.search(r'<invoke\s+name=["\']([^"\']+)["\']', match)
                if not name_match:
                    continue
                tool_name = name_match.group(1)

                params = {}
                for param in re.finditer(
                    r'<parameter\s+name=["\']([^"\']+)["\']>(.*?)</parameter>',
                    match,
                    re.DOTALL,
                ):
                    params[param.group(1)] = param.group(2).strip()

                tool_calls.append(
                    {
                        "id": f"tool_{secrets.token_hex(8)}",
                        "name": tool_name,
                        "input": params,
                    }
                )
            except Exception as e:
                logger.warning(f"解析 minimax tool_call 失败: {e}")

        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return clean_text, tool_calls


# 全局单例（默认配置）
llm_service = LLMService()
