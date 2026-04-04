# -*- coding: utf-8 -*-
"""
OpenAI Provider - OpenAI 兼容 API 调用（chat + stream）
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator

from openai import OpenAI

logger = logging.getLogger(__name__)


def convert_tools_to_openai_format(tools: List[Dict]) -> List[Dict]:
    """将Anthropic格式的工具转换为OpenAI格式"""
    openai_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
            )
    return openai_tools


def convert_to_openai_messages(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """转换消息为 OpenAI API 格式"""
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
                openai_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            if isinstance(content, str):
                openai_messages.append({"role": "assistant", "content": content})
            else:
                assistant_msg = {"role": "assistant", "content": ""}
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type == "text":
                            assistant_msg["content"] = block.get("text", "")
                        elif block_type == "tool_use":
                            tool_calls.append(
                                {
                                    "id": block.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name", ""),
                                        "arguments": json.dumps(
                                            block.get("input", {})
                                        ),
                                    },
                                }
                            )
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                openai_messages.append(assistant_msg)

    return openai_messages


async def chat_openai(
    base_url: str,
    model: str,
    messages: List[Dict[str, Any]],
    openai_messages: List[Dict[str, Any]],
    tools: List[Dict] = None,
    tools_enabled: bool = True,
    api_key: str = "",
) -> Dict[str, Any]:
    """调用OpenAI兼容API"""
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)

        request_kwargs = {
            "model": model,
            "messages": openai_messages,
            "temperature": 1.0,
        }
        if tools_enabled and tools:
            request_kwargs["tools"] = convert_tools_to_openai_format(tools)

        response = await asyncio.to_thread(
            client.chat.completions.create, **request_kwargs
        )

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
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    }
                )
                result_content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    }
                )

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


async def chat_stream_openai(
    base_url: str,
    model: str,
    openai_messages: List[Dict[str, Any]],
    tools: List[Dict] = None,
    tools_enabled: bool = True,
    api_key: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """流式调用OpenAI兼容API"""
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)

        request_kwargs = {
            "model": model,
            "messages": openai_messages,
            "temperature": 1.0,
            "stream": True,
        }
        if tools_enabled and tools:
            openai_tools = convert_tools_to_openai_format(tools)
            if openai_tools:
                request_kwargs["tools"] = openai_tools
                logger.info(f"启用工具调用，发送 {len(openai_tools)} 个工具")

        accumulated_text = ""
        tool_calls = []
        content_blocks = []

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
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    }
                )
                yield {"type": "tool_use_start", "id": tc["id"], "name": tc["name"]}
                yield {
                    "type": "tool_input_ready",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
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
