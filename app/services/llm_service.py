# -*- coding: utf-8 -*-
"""
LLM Service - 大模型调用服务 (Anthropic兼容)
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
from app.config import get_settings
from app.services.mcp_tool_registry import mcp_tool_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """LLM服务 (Anthropic API)"""

    def __init__(self):
        self.base_url = "https://api.minimaxi.com/anthropic"
        self.model = settings.llm_model

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具定义（从mcp_tool_registry获取）"""
        return mcp_tool_registry.get_tool_definitions()

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

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool = True,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用LLM API (Anthropic兼容)"""
        try:
            # 使用传入的API Key或配置中的默认Key
            effective_api_key = api_key or settings.llm_api_key
            if not effective_api_key:
                return {
                    "error": "LLM API Key未配置",
                    "tool_calls": [],
                    "content_blocks": [],
                }

            client = anthropic.Anthropic(
                base_url=self.base_url,
                api_key=effective_api_key,
            )

            # 转换消息格式
            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(messages)

            # 构建请求
            request_kwargs = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": anthropic_messages,
                "temperature": 1.0,
            }

            if system_prompt:
                request_kwargs["system"] = system_prompt

            if tools_enabled:
                request_kwargs["tools"] = self.get_tools()

            # 调用API
            response = await asyncio.to_thread(client.messages.create, **request_kwargs)

            # 解析响应
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
            logger.error(f"LLM调用异常: {str(e)}")
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
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用LLM API (Anthropic兼容)"""
        try:
            effective_api_key = api_key or settings.llm_api_key
            if not effective_api_key:
                yield {"type": "error", "error": "LLM API Key未配置"}
                return

            client = anthropic.Anthropic(
                base_url=self.base_url,
                api_key=effective_api_key,
            )

            # 转换消息格式
            system_prompt, anthropic_messages = self._convert_to_anthropic_messages(messages)

            request_kwargs = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": anthropic_messages,
                "temperature": 1.0,
            }
            if system_prompt:
                request_kwargs["system"] = system_prompt
            if tools_enabled:
                tools = self.get_tools()
                request_kwargs["tools"] = tools
                tool_names = [t.get('name') for t in tools]
                logger.info(f"启用工具调用，发送 {len(tools)} 个工具: {', '.join(tool_names)}")
            else:
                logger.info("工具调用已禁用")

            # 在线程中运行同步流，避免阻塞事件循环
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
            text_block_yielded_len = 0  # tracks how many chars of accumulated_text have been sent as text_delta
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
                                text_block_yielded_len = 0  # reset for each new text block
                            elif current_block_type == "thinking":
                                # thinking 块开始
                                logger.info(
                                    "[LLM Event] content_block_start - thinking block started"
                                )
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
                                logger.debug(f"收到文本增量: {text[:50]}...")
                                # 避免将 XML 工具调用标签（<minimax:tool_call>）的任何部分发送给前端
                                # 使用 '<minimax' 作为更早的检测点，防止分块传输时的标签截断问题
                                if "<minimax:tool_call>" not in accumulated_text:
                                    xml_start_idx = accumulated_text.find("<minimax")
                                    if xml_start_idx == -1:
                                        # 无 XML 标记，安全发送所有未发送的文本
                                        unsent = accumulated_text[text_block_yielded_len:]
                                        if unsent:
                                            yield {"type": "text_delta", "text": unsent}
                                            text_block_yielded_len = len(accumulated_text)
                                    else:
                                        # 发现潜在 XML 起始位置，只发送其前面的安全文本
                                        safe_text = accumulated_text[text_block_yielded_len:xml_start_idx]
                                        if safe_text:
                                            yield {"type": "text_delta", "text": safe_text}
                                            text_block_yielded_len = xml_start_idx
                                        # xml_start_idx 之后的内容暂不发送，等待判断是否为 XML 标签
                                # 如果 accumulated_text 已包含完整 XML 标签，不再发送新增量
                            elif delta_type == "thinking_delta":
                                thinking_text = getattr(delta, "thinking", "")
                                logger.info(
                                    f"[LLM Event] thinking_delta: {thinking_text[:100]}..."
                                )
                                # 发送 thinking 增量到前端
                                yield {
                                    "type": "thinking_delta",
                                    "thinking": thinking_text,
                                }
                            elif delta_type == "tool_use":
                                logger.info(f"收到原生 tool_use 增量")
                            else:
                                logger.debug(f"收到其他类型增量: {delta_type}")

                    elif event_type == "content_block_stop":
                        if current_block_type == "text":
                            # 解析 minimax XML 工具调用（MiniMax 不支持原生 tool_use，用 XML 代替）
                            clean_text, xml_tool_calls = self._parse_minimax_tool_calls(
                                accumulated_text
                            )
                            if xml_tool_calls:
                                # 有 XML 工具调用，用解析出的工具调用替代
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
                                    # 发送工具调用开始事件（为每个解析出的工具调用）
                                    yield {
                                        "type": "tool_use_start",
                                        "id": tc["id"],
                                        "name": tc["name"],
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
                                # 无 XML 工具调用：发送所有尚未发送的剩余文本（如有因 '<minimax' 误判而缓冲的部分）
                                remaining = accumulated_text[text_block_yielded_len:]
                                if remaining:
                                    yield {"type": "text_delta", "text": remaining}
                                    text_block_yielded_len = len(accumulated_text)
                                content_blocks.append(
                                    {"type": "text", "text": accumulated_text}
                                )
                                yield {"type": "text_stop", "text": accumulated_text}
                        elif current_block_type == "tool_use":
                            yield {"type": "tool_use_stop"}

            # 解析最终消息的所有内容块（重要！）
            # 统一从 final_message 解析，避免与 content_block_stop 重复
            if final_message:
                logger.info(
                    f"流结束，最终消息包含 {len(final_message.content)} 个内容块"
                )
                # 清空并重新从 final_message 构建
                content_blocks = []
                tool_calls = []  # 也重新构建 tool_calls
                
                for block in final_message.content:
                    block_type = block.type
                    logger.info(f"  内容块类型: {block_type}")
                    
                    if block_type == "tool_use":
                        logger.info(f"  发现原生 tool_use: {block.name}")
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
                        # 添加文本块
                        text_content = getattr(block, "text", "")
                        content_blocks.append({
                            "type": "text",
                            "text": text_content
                        })
                        # 更新 accumulated_text
                        if text_content:
                            accumulated_text = text_content
                    elif block_type == "thinking":
                        # 添加思考块
                        thinking_content = getattr(block, "thinking", "")
                        content_blocks.append({
                            "type": "thinking",
                            "thinking": thinking_content
                        })

            logger.info(
                f"[LLM Event] stream_end - tool_calls: {[tc.get('name') for tc in tool_calls]}, content_blocks: {len(content_blocks)}, accumulated_text: {len(accumulated_text)}, yielded: {text_block_yielded_len}"
            )
            
            # 如果 accumulated_text 有内容但之前没有发送过（MiniMax 可能只在 final_message 中返回文本）
            # 需要在 stream_end 之前发送 text_delta
            if accumulated_text and text_block_yielded_len < len(accumulated_text):
                remaining_text = accumulated_text[text_block_yielded_len:]
                if remaining_text:
                    logger.info(f"[LLM Event] 发送剩余文本: {len(remaining_text)} 字符")
                    yield {"type": "text_delta", "text": remaining_text}
            
            yield {
                "type": "stream_end",
                "content": accumulated_text,
                "content_blocks": content_blocks,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.error(f"LLM流式调用异常: {str(e)}")
            yield {"type": "error", "error": str(e)}

    def _parse_minimax_tool_calls(self, text: str):
        """
        解析 MiniMax 返回的 XML 格式工具调用
        格式: <minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>
        返回: (clean_text, tool_calls)
        """
        import re
        import secrets

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

        # 移除 XML 标记，保留前后的普通文本
        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return clean_text, tool_calls


# 全局单例
llm_service = LLMService()
