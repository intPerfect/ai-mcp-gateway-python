# -*- coding: utf-8 -*-
"""
Anthropic Provider - Anthropic API 调用（chat + stream）
"""

import json
import logging
import asyncio
import queue
import threading
from typing import List, Dict, Any, AsyncGenerator

import anthropic

from app.services.llm.minimax_parser import parse_minimax_tool_calls

logger = logging.getLogger(__name__)


async def chat_anthropic(
    base_url: str,
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: str,
    anthropic_messages: List[Dict[str, Any]],
    tools: List[Dict] = None,
    tools_enabled: bool = True,
    api_key: str = "",
) -> Dict[str, Any]:
    """调用Anthropic API"""
    try:
        client = anthropic.Anthropic(base_url=base_url, api_key=api_key)

        request_kwargs = {
            "model": model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "temperature": 1.0,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        if tools_enabled and tools:
            request_kwargs["tools"] = tools

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


async def chat_stream_anthropic(
    base_url: str,
    model: str,
    system_prompt: str,
    anthropic_messages: List[Dict[str, Any]],
    tools: List[Dict] = None,
    tools_enabled: bool = True,
    api_key: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """流式调用Anthropic API"""
    try:
        client = anthropic.Anthropic(base_url=base_url, api_key=api_key)

        request_kwargs = {
            "model": model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "temperature": 1.0,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        if tools_enabled and tools:
            request_kwargs["tools"] = tools
            tool_names = [t.get("name") for t in tools]
            logger.info(
                f"启用工具调用，发送 {len(tools)} 个工具: {', '.join(tool_names)}"
            )
        else:
            logger.info("工具调用已禁用")

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
        # 工具参数流式累积
        current_tool_id = ""
        current_tool_name = ""
        current_tool_input_json = ""

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
                            logger.info(
                                "[LLM Event] content_block_start - thinking block started"
                            )
                        elif current_block_type == "tool_use":
                            current_tool_id = getattr(content_block, "id", "")
                            current_tool_name = getattr(content_block, "name", "")
                            current_tool_input_json = ""
                            yield {
                                "type": "tool_use_start",
                                "id": current_tool_id,
                                "name": current_tool_name,
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
                                    safe_text = accumulated_text[
                                        text_block_yielded_len:xml_start_idx
                                    ]
                                    if safe_text:
                                        yield {"type": "text_delta", "text": safe_text}
                                        text_block_yielded_len = xml_start_idx
                        elif delta_type == "input_json_delta":
                            partial_json = getattr(delta, "partial_json", "")
                            if partial_json:
                                current_tool_input_json += partial_json
                        elif delta_type == "thinking_delta":
                            thinking_text = getattr(delta, "thinking", "")
                            yield {
                                "type": "thinking_delta",
                                "thinking": thinking_text,
                            }
                elif event_type == "content_block_stop":
                    if current_block_type == "text":
                        clean_text, xml_tool_calls = parse_minimax_tool_calls(
                            accumulated_text
                        )
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
                                # MiniMax XML路径：立即发送参数
                                yield {
                                    "type": "tool_input_ready",
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "input": tc["input"],
                                }
                                yield {"type": "tool_use_stop"}
                            if clean_text:
                                content_blocks.append(
                                    {"type": "text", "text": clean_text}
                                )
                                yield {"type": "text_stop", "text": clean_text}
                            else:
                                yield {"type": "text_stop", "text": ""}
                        else:
                            remaining = accumulated_text[text_block_yielded_len:]
                            if remaining:
                                yield {"type": "text_delta", "text": remaining}
                                text_block_yielded_len = len(accumulated_text)
                            content_blocks.append(
                                {"type": "text", "text": accumulated_text}
                            )
                            yield {"type": "text_stop", "text": accumulated_text}
                    elif current_block_type == "tool_use":
                        # 解析累积的工具参数并发送
                        parsed_input = {}
                        if current_tool_input_json:
                            try:
                                parsed_input = json.loads(current_tool_input_json)
                            except Exception:
                                parsed_input = {"_raw": current_tool_input_json}
                        yield {
                            "type": "tool_input_ready",
                            "id": current_tool_id,
                            "name": current_tool_name,
                            "input": parsed_input,
                        }
                        yield {"type": "tool_use_stop"}

        # 保存流式阶段解析的 tool_calls（如 MiniMax XML 解析的，ID 与前端一致）
        streaming_tool_calls = list(tool_calls)

        if final_message:
            logger.info(
                f"流结束，最终消息包含 {len(final_message.content)} 个内容块"
            )
            content_blocks = []
            final_tool_calls = []

            for block in final_message.content:
                block_type = block.type
                if block_type == "tool_use":
                    final_tool_calls.append(
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
                    content_blocks.append(
                        {"type": "thinking", "thinking": thinking_content}
                    )

            # 如果流式阶段已有 tool_calls（如 MiniMax XML 解析），保留其 ID（与前端一致）
            # 但用 final_message 的 input 更新（更可靠的解析）
            if streaming_tool_calls:
                for i, stc in enumerate(streaming_tool_calls):
                    if i < len(final_tool_calls):
                        stc["input"] = final_tool_calls[i].get("input", stc["input"])
                tool_calls = streaming_tool_calls
            else:
                tool_calls = final_tool_calls

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
