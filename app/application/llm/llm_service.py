# -*- coding: utf-8 -*-
"""
LLM Service - LLM应用服务
封装LLM调用逻辑
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
import asyncio

from app.config import get_settings
from app.domain.tool.registry import mcp_tool_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """LLM应用服务 (Anthropic API)"""
    
    def __init__(self):
        self.base_url = "https://api.minimaxi.com/anthropic"
        self.model = settings.llm_model
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具定义"""
        return mcp_tool_registry.get_tool_definitions()
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        return await mcp_tool_registry.execute_tool(tool_name, arguments)
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool = True,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用LLM API (Anthropic兼容)"""
        try:
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
            anthropic_messages, system_prompt = self._convert_messages(messages)

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
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"LLM调用异常: {str(e)}")
            return {
                "content": f"LLM调用异常: {str(e)}",
                "error": str(e),
                "tool_calls": [],
                "content_blocks": [],
            }
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools_enabled: bool = True,
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用LLM API"""
        try:
            effective_api_key = api_key or settings.llm_api_key
            if not effective_api_key:
                yield {"type": "error", "error": "LLM API Key未配置"}
                return

            client = anthropic.Anthropic(
                base_url=self.base_url,
                api_key=effective_api_key,
            )

            anthropic_messages, system_prompt = self._convert_messages(messages)

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
                logger.info(f"启用工具调用，发送 {len(tools)} 个工具")

            # 在线程中运行同步流
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
            
            async for event in self._process_stream_events(loop, result_queue):
                yield event

        except Exception as e:
            logger.error(f"LLM流式调用异常: {str(e)}")
            yield {"type": "error", "error": str(e)}
    
    def _convert_messages(self, messages: List[Dict]) -> tuple:
        """转换消息格式"""
        anthropic_messages = []
        system_prompt = ""

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content if isinstance(content, str) else str(content)
            elif role == "user":
                if isinstance(content, str):
                    anthropic_messages.append({
                        "role": "user",
                        "content": [{"type": "text", "text": content}],
                    })
                else:
                    anthropic_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                if isinstance(content, str):
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": [{"type": "text", "text": content}],
                    })
                else:
                    assistant_content, tool_result_content = self._parse_assistant_content(content)
                    if assistant_content:
                        anthropic_messages.append({"role": "assistant", "content": assistant_content})
                    if tool_result_content:
                        anthropic_messages.append({"role": "user", "content": tool_result_content})

        return anthropic_messages, system_prompt
    
    def _parse_assistant_content(self, content):
        """解析助手内容"""
        assistant_content = []
        tool_result_content = []
        
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "thinking":
                    assistant_content.append({
                        "type": "thinking",
                        "thinking": block.get("thinking", ""),
                    })
                elif block_type == "text":
                    assistant_content.append({
                        "type": "text", 
                        "text": block.get("text", "")
                    })
                elif block_type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}),
                    })
                elif block_type == "tool_result":
                    tool_result_content.append({
                        "type": "tool_result",
                        "tool_use_id": block.get("tool_use_id", ""),
                        "content": block.get("content", ""),
                    })
        
        return assistant_content, tool_result_content
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """解析响应"""
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
                tool_calls.append({
                    "id": block.id, 
                    "name": block.name, 
                    "input": block.input
                })
            elif block.type == "thinking":
                block_dict["thinking"] = getattr(block, "thinking", "")

            result_content_blocks.append(block_dict)

        return {
            "content": result_content,
            "content_blocks": result_content_blocks,
            "tool_calls": tool_calls,
        }
    
    async def _process_stream_events(self, loop, result_queue):
        """处理流事件"""
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
                async for event in self._handle_stream_event(
                    payload, current_block_type, accumulated_text, 
                    text_block_yielded_len, tool_calls, content_blocks
                ):
                    if event.get("update_state"):
                        if event.get("current_block_type") is not None:
                            current_block_type = event["current_block_type"]
                        if event.get("accumulated_text") is not None:
                            accumulated_text = event["accumulated_text"]
                        if event.get("text_block_yielded_len") is not None:
                            text_block_yielded_len = event["text_block_yielded_len"]
                    else:
                        yield event

        # 处理最终消息
        if final_message:
            content_blocks, tool_calls, accumulated_text = self._process_final_message(
                final_message, content_blocks, tool_calls
            )

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
    
    async def _handle_stream_event(self, event, current_block_type, accumulated_text, 
                                    text_block_yielded_len, tool_calls, content_blocks):
        """处理单个流事件"""
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            yield {"type": "stream_start"}

        elif event_type == "content_block_start":
            content_block = getattr(event, "content_block", None)
            if content_block:
                current_block_type = getattr(content_block, "type", None)
                if current_block_type == "text":
                    yield {"update_state": True, "current_block_type": current_block_type, 
                           "accumulated_text": "", "text_block_yielded_len": 0}
                elif current_block_type == "tool_use":
                    yield {"type": "tool_use_start", "id": getattr(content_block, "id", ""),
                           "name": getattr(content_block, "name", "")}

        elif event_type == "content_block_delta":
            delta = getattr(event, "delta", None)
            if delta:
                delta_type = getattr(delta, "type", None)
                if delta_type == "text_delta":
                    text = getattr(delta, "text", "")
                    accumulated_text += text
                    yield {"type": "text_delta", "text": text, "update_state": True,
                           "accumulated_text": accumulated_text}
                elif delta_type == "thinking_delta":
                    thinking_text = getattr(delta, "thinking", "")
                    yield {"type": "thinking_delta", "thinking": thinking_text}

        elif event_type == "content_block_stop":
            if current_block_type == "tool_use":
                yield {"type": "tool_use_stop"}
    
    def _process_final_message(self, final_message, content_blocks, tool_calls):
        """处理最终消息"""
        accumulated_text = ""
        content_blocks = []
        tool_calls = []
        
        for block in final_message.content:
            block_type = block.type
            
            if block_type == "tool_use":
                tool_calls.append({
                    "id": block.id, 
                    "name": block.name, 
                    "input": block.input
                })
                content_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            elif block_type == "text":
                text_content = getattr(block, "text", "")
                content_blocks.append({
                    "type": "text",
                    "text": text_content
                })
                if text_content:
                    accumulated_text = text_content
            elif block_type == "thinking":
                thinking_content = getattr(block, "thinking", "")
                content_blocks.append({
                    "type": "thinking",
                    "thinking": thinking_content
                })
        
        return content_blocks, tool_calls, accumulated_text
    
    def _parse_minimax_tool_calls(self, text: str):
        """解析 MiniMax 返回的 XML 格式工具调用"""
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

                tool_calls.append({
                    "id": f"tool_{secrets.token_hex(8)}",
                    "name": tool_name,
                    "input": params,
                })
            except Exception as e:
                logger.warning(f"解析 minimax tool_call 失败: {e}")

        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return clean_text, tool_calls


# 全局单例
llm_service = LLMService()
