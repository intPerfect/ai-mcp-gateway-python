# -*- coding: utf-8 -*-
"""
Chat Service - 对话服务
实现健壮的多轮工具调用循环，解决工具调用后 LLM 不继续响应的问题
"""

import json
import logging
import secrets
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from app.services.message_manager import (
    MessageHistory, Message, ContentBlock, TextBlock, ThinkingBlock, 
    ToolUseBlock, ToolResultBlock, MessageBuilder, DEFAULT_SYSTEM_PROMPT
)
from app.services.conversation_logger import conversation_logger, LogEventType
from app.services.llm_service import llm_service
from app.services.websocket_protocol import WSEventFactory
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatState(Enum):
    """对话状态"""
    IDLE = "idle"
    PROCESSING = "processing"
    TOOL_CALLING = "tool_calling"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_use_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool = True
    error: str = ""


class ChatSession:
    """对话会话"""
    
    def __init__(
        self,
        session_id: str,
        gateway_key: str = "",
        llm_key: str = "",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ):
        self.session_id = session_id
        self.gateway_key = gateway_key
        self.llm_key = llm_key
        self.message_history = MessageHistory(system_prompt)
        self.state = ChatState.IDLE
        
        # 统计信息
        self.total_tool_rounds = 0
        self.tools_called: List[str] = []
        self.accumulated_thinking = ""  # 累积的思考内容
        self.accumulated_text = ""  # 累积的文本内容
    
    def reset_for_new_turn(self):
        """为新一轮对话重置累积内容（但保留历史）"""
        self.accumulated_thinking = ""
        self.accumulated_text = ""
        self.state = ChatState.IDLE


class ChatService:
    """对话服务"""
    
    MAX_TOOL_ROUNDS = 10  # 最大工具调用轮次
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(
        self,
        session_id: str,
        gateway_key: str = "",
        llm_key: str = "",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ) -> ChatSession:
        """创建会话"""
        session = ChatSession(
            session_id=session_id,
            gateway_key=gateway_key,
            llm_key=llm_key,
            system_prompt=system_prompt
        )
        self.sessions[session_id] = session
        logger.info(f"创建对话会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"移除对话会话: {session_id}")
    
    async def chat_stream(
        self,
        session_id: str,
        user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话主入口
        
        解决的核心问题：
        1. 正确处理多轮工具调用
        2. 工具调用后 LLM 必须给出响应
        3. 合并 thinking 输出，避免前端分裂
        """
        session = self.sessions.get(session_id)
        if not session:
            yield WSEventFactory.error("会话不存在")
            return
        
        try:
            session.state = ChatState.PROCESSING
            
            # 1. 记录用户输入
            await conversation_logger.log_user_input(session_id, user_message)
            session.message_history.add_user_message(user_message)
            
            # 2. 发送流开始事件
            yield WSEventFactory.stream_start()
            
            # 3. 执行对话循环（可能包含多轮工具调用）
            async for event in self._chat_loop(session):
                yield event
            
        except Exception as e:
            logger.error(f"对话处理异常: {e}", exc_info=True)
            await conversation_logger.log_error(session_id, str(e))
            yield WSEventFactory.error(str(e))
        finally:
            session.state = ChatState.IDLE
    
    async def _chat_loop(self, session: ChatSession) -> AsyncGenerator[Dict[str, Any], None]:
        """
        对话主循环
        
        核心逻辑：
        1. 调用 LLM
        2. 如果有工具调用，执行工具，添加结果到历史，继续循环
        3. 如果没有工具调用，结束循环
        4. 确保每轮都有正确的响应
        """
        round_num = 0
        pending_tool_calls: List[Dict] = []
        
        while round_num < self.MAX_TOOL_ROUNDS:
            round_num += 1
            logger.info(f"[{session.session_id}] 开始第 {round_num} 轮对话")
            
            # 记录 LLM 请求
            await conversation_logger.log_llm_request(
                session.session_id,
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                round_num=round_num
            )
            
            # 当前轮次的累积内容
            round_text = ""
            round_thinking = ""
            round_tool_calls: List[Dict] = []
            round_content_blocks: List[ContentBlock] = []
            
            # 调用 LLM 流式 API
            async for llm_event in llm_service.chat_stream(
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                api_key=session.llm_key or None
            ):
                event_type = llm_event.get("type")
                
                if event_type == "text_delta":
                    text = llm_event.get("text", "")
                    round_text += text
                    session.accumulated_text += text
                    # 直接转发文本增量
                    yield WSEventFactory.text_delta(text)
                
                elif event_type == "thinking_delta":
                    thinking = llm_event.get("thinking", "")
                    round_thinking += thinking
                    session.accumulated_thinking += thinking
                    # 记录思考日志
                    await conversation_logger.log_llm_thinking(
                        session.session_id, thinking, round_num
                    )
                    # 发送思考增量，包含轮次信息，前端根据轮次创建独立块
                    yield WSEventFactory.thinking_delta(thinking, round_thinking, round_num)
                
                elif event_type == "tool_use_start":
                    tool_id = llm_event.get("id", "")
                    tool_name = llm_event.get("name", "")
                    yield WSEventFactory.tool_use_start(tool_id, tool_name)
                
                elif event_type == "tool_use_stop":
                    yield WSEventFactory.tool_use_stop()
                
                elif event_type == "stream_end":
                    # 获取本轮完整响应
                    round_content_blocks = llm_event.get("content_blocks", [])
                    round_tool_calls = llm_event.get("tool_calls", [])
                    
                    # 优先从 content_blocks 提取文本（从 final_message 解析的完整内容）
                    if round_content_blocks:
                        for block in round_content_blocks:
                            if block.get("type") == "text":
                                round_text = block.get("text", "")
                                logger.info(f"[{session.session_id}] 从 content_blocks 获取文本: {len(round_text)} 字符")
                                break
                    
                    # 备用：从 stream_end 的 content 字段获取累积文本
                    if not round_text:
                        stream_content = llm_event.get("content", "")
                        if stream_content:
                            round_text = stream_content
                            logger.info(f"[{session.session_id}] 从 stream_end.content 获取文本: {len(stream_content)} 字符")
                    
                    # 更新会话累积文本
                    if round_text:
                        session.accumulated_text = round_text
                
                elif event_type == "error":
                    error_msg = llm_event.get("error", "未知错误")
                    await conversation_logger.log_error(session.session_id, error_msg)
                    yield WSEventFactory.error(error_msg)
                    return
            
            # 记录 LLM 响应
            await conversation_logger.log_llm_response(
                session.session_id,
                round_text,
                round_tool_calls,
                round_num
            )
            
            # 构建助手响应内容块并保存到历史
            assistant_blocks = MessageBuilder.build_assistant_response(
                text=round_text,
                thinking=round_thinking,
                tool_calls=round_tool_calls
            )
            
            # 只添加非空响应到历史
            if assistant_blocks:
                session.message_history.add_assistant_message(assistant_blocks)
            elif round_text:
                session.message_history.add_assistant_message(round_text)
            
            # 检查是否有工具调用
            if not round_tool_calls:
                # 没有工具调用，对话结束
                logger.info(f"[{session.session_id}] 第 {round_num} 轮无工具调用，对话结束")
                
                # 确保有最终文本响应
                final_text = session.accumulated_text or round_text
                if final_text:
                    yield WSEventFactory.response(
                        final_text, 
                        session.accumulated_thinking, 
                        session.tools_called, 
                        round_num
                    )
                else:
                    # 没有任何响应，提示用户
                    yield WSEventFactory.response(
                        "我已完成处理，但没有生成具体回复。请问还有其他需要帮助的吗？",
                        session.accumulated_thinking,
                        session.tools_called,
                        round_num
                    )
                
                break
            
            # 有工具调用，执行工具
            logger.info(f"[{session.session_id}] 第 {round_num} 轮有 {len(round_tool_calls)} 个工具调用")
            
            # 发送工具执行状态
            yield WSEventFactory.status(
                "executing_tools", 
                f"正在执行 {len(round_tool_calls)} 个工具...",
                tool_calls=round_tool_calls
            )
            
            # 执行所有工具并发送每个工具的事件
            tool_results = []
            for tool_call in round_tool_calls:
                tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("input", {})
                
                # 发送工具调用开始事件
                yield WSEventFactory.tool_call(tool_id, tool_name, arguments, "executing")
                
                # 执行单个工具
                result = await self._execute_single_tool(session, tool_id, tool_name, arguments, round_num)
                tool_results.append(result)
                
                # 发送工具结果事件
                yield WSEventFactory.tool_result(tool_id, tool_name, result.result, result.success)
            
            # 将工具结果添加到消息历史
            tool_result_blocks = []
            for tr in tool_results:
                tool_result_blocks.append({
                    "tool_use_id": tr.tool_use_id,
                    "result": tr.result,
                    "is_error": not tr.success
                })
            
            session.message_history.add_tool_results_batch(tool_result_blocks)
            
            # 发送工具执行完成状态
            yield WSEventFactory.status(
                "tools_completed", 
                f"第 {round_num} 轮工具执行完成，继续推理..."
            )
            
            # 继续下一轮循环...
        
        else:
            # 达到最大轮次限制
            logger.warning(f"[{session.session_id}] 达到最大工具调用轮次 {self.MAX_TOOL_ROUNDS}")
            event = WSEventFactory.response(
                "我已执行了多轮工具调用，达到了处理上限。请告诉我是否需要继续执行更多操作？",
                session.accumulated_thinking,
                session.tools_called,
                round_num
            )
            event["limit_reached"] = True
            yield event
        
        # 记录会话结束
        await conversation_logger.log_session_end(
            session.session_id,
            round_num,
            session.tools_called
        )
    
    async def _execute_single_tool(
        self,
        session: ChatSession,
        tool_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        round_num: int
    ) -> ToolCallResult:
        """执行单个工具调用"""
        logger.info(f"[{session.session_id}] 执行工具: {tool_name}, 参数: {arguments}")
        
        # 记录工具调用
        await conversation_logger.log_tool_call(
            session.session_id, tool_id, tool_name, arguments, round_num
        )
        
        try:
            # 执行工具
            result = await llm_service.execute_tool(tool_name, arguments)
            
            # 记录成功
            await conversation_logger.log_tool_result(
                session.session_id, tool_id, tool_name, result, True, round_num
            )
            
            session.tools_called.append(tool_name)
            
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=True
            )
            
        except Exception as e:
            logger.error(f"[{session.session_id}] 工具执行失败: {tool_name}, 错误: {e}")
            
            error_result = {"error": str(e)}
            await conversation_logger.log_tool_result(
                session.session_id, tool_id, tool_name, error_result, False, round_num
            )
            
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                arguments=arguments,
                result=error_result,
                success=False,
                error=str(e)
            )
    
    async def _execute_tools(
        self,
        session: ChatSession,
        tool_calls: List[Dict],
        round_num: int
    ) -> List[ToolCallResult]:
        """执行工具调用"""
        results = []
        
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("input", {})
            
            logger.info(f"[{session.session_id}] 执行工具: {tool_name}, 参数: {arguments}")
            
            # 记录工具调用
            await conversation_logger.log_tool_call(
                session.session_id, tool_id, tool_name, arguments, round_num
            )
            
            # 发送工具调用事件
            # (这里由 WebSocket handler 处理，不在此处发送)
            
            try:
                # 执行工具
                result = await llm_service.execute_tool(tool_name, arguments)
                
                # 记录成功
                results.append(ToolCallResult(
                    tool_use_id=tool_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    success=True
                ))
                
                # 记录工具结果
                await conversation_logger.log_tool_result(
                    session.session_id, tool_id, tool_name, result, True, round_num
                )
                
                session.tools_called.append(tool_name)
                
            except Exception as e:
                logger.error(f"[{session.session_id}] 工具执行失败: {tool_name}, 错误: {e}")
                
                error_result = {"error": str(e)}
                results.append(ToolCallResult(
                    tool_use_id=tool_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=error_result,
                    success=False,
                    error=str(e)
                ))
                
                # 记录失败
                await conversation_logger.log_tool_result(
                    session.session_id, tool_id, tool_name, error_result, False, round_num
                )
        
        return results
    
    def clear_session(self, session_id: str, keep_system: bool = True):
        """清空会话历史"""
        session = self.sessions.get(session_id)
        if session:
            session.message_history.clear(keep_system)
            session.accumulated_thinking = ""
            session.accumulated_text = ""
            session.tools_called = []
            session.total_tool_rounds = 0
            logger.info(f"清空会话历史: {session_id}")


# 全局单例
chat_service = ChatService()