# -*- coding: utf-8 -*-
"""
Chat Service - 对话应用服务
编排对话用例，协调领域服务
"""
import logging
from typing import Any, Dict, Optional, AsyncGenerator

from app.domain.chat.models import ChatSession, ChatState, ToolCallResult
from app.domain.chat.history import MessageBuilder
from app.infrastructure.logging.conversation_logger import conversation_logger
from app.application.llm.llm_service import llm_service
from app.domain.protocol.websocket import WSEventFactory

logger = logging.getLogger(__name__)


class ChatService:
    """对话应用服务"""
    
    MAX_TOOL_ROUNDS = 10  # 最大工具调用轮次
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(
        self,
        session_id: str,
        gateway_key: str = "",
        llm_key: str = "",
        system_prompt: str = ""
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
        """对话主循环"""
        round_num = 0
        
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
            round_tool_calls = []
            
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
                    yield WSEventFactory.text_delta(text)
                
                elif event_type == "thinking_delta":
                    thinking = llm_event.get("thinking", "")
                    round_thinking += thinking
                    session.accumulated_thinking += thinking
                    await conversation_logger.log_llm_thinking(
                        session.session_id, thinking, round_num
                    )
                    yield WSEventFactory.thinking_delta(thinking, round_thinking, round_num)
                
                elif event_type == "tool_use_start":
                    tool_id = llm_event.get("id", "")
                    tool_name = llm_event.get("name", "")
                    yield WSEventFactory.tool_use_start(tool_id, tool_name)
                
                elif event_type == "tool_use_stop":
                    yield WSEventFactory.tool_use_stop()
                
                elif event_type == "stream_end":
                    round_tool_calls = llm_event.get("tool_calls", [])
                    content_blocks = llm_event.get("content_blocks", [])
                    if content_blocks:
                        for block in content_blocks:
                            if block.get("type") == "text":
                                round_text = block.get("text", "")
                                break
                
                elif event_type == "error":
                    yield WSEventFactory.error(llm_event.get("error", "未知错误"))
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
            
            if assistant_blocks:
                session.message_history.add_assistant_message(assistant_blocks)
            elif round_text:
                session.message_history.add_assistant_message(round_text)
            
            # 检查是否有工具调用
            if not round_tool_calls:
                # 没有工具调用，对话结束
                logger.info(f"[{session.session_id}] 第 {round_num} 轮无工具调用，对话结束")
                
                final_text = session.accumulated_text or round_text
                if final_text:
                    yield WSEventFactory.response(
                        final_text, 
                        session.accumulated_thinking, 
                        session.tools_called, 
                        round_num
                    )
                else:
                    yield WSEventFactory.response(
                        "我已完成处理，但没有生成具体回复。请问还有其他需要帮助的吗？",
                        session.accumulated_thinking,
                        session.tools_called,
                        round_num
                    )
                
                break
            
            # 有工具调用，执行工具
            logger.info(f"[{session.session_id}] 第 {round_num} 轮有 {len(round_tool_calls)} 个工具调用")
            
            yield WSEventFactory.status(
                "executing_tools", 
                f"正在执行 {len(round_tool_calls)} 个工具...",
                tool_calls=round_tool_calls
            )
            
            # 执行所有工具
            tool_results = await self._execute_tools(session, round_tool_calls, round_num)
            
            # 将工具结果添加到消息历史
            tool_result_blocks = []
            for tr in tool_results:
                tool_result_blocks.append({
                    "tool_use_id": tr.tool_use_id,
                    "result": tr.result,
                    "is_error": not tr.success
                })
            
            session.message_history.add_tool_results_batch(tool_result_blocks)
            
            yield WSEventFactory.status(
                "tools_completed", 
                f"第 {round_num} 轮工具执行完成，继续推理..."
            )
        
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
    
    async def _execute_tools(
        self,
        session: ChatSession,
        tool_calls: List[Dict],
        round_num: int
    ) -> List[ToolCallResult]:
        """执行工具调用"""
        import secrets
        results = []
        
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("input", {})
            
            logger.info(f"[{session.session_id}] 执行工具: {tool_name}, 参数: {arguments}")
            
            await conversation_logger.log_tool_call(
                session.session_id, tool_id, tool_name, arguments, round_num
            )
            
            try:
                result = await llm_service.execute_tool(tool_name, arguments)
                
                await conversation_logger.log_tool_result(
                    session.session_id, tool_id, tool_name, result, True, round_num
                )
                
                session.tools_called.append(tool_name)
                
                results.append(ToolCallResult(
                    tool_use_id=tool_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    success=True
                ))
                
            except Exception as e:
                logger.error(f"[{session.session_id}] 工具执行失败: {tool_name}, 错误: {e}")
                
                error_result = {"error": str(e)}
                await conversation_logger.log_tool_result(
                    session.session_id, tool_id, tool_name, error_result, False, round_num
                )
                
                results.append(ToolCallResult(
                    tool_use_id=tool_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=error_result,
                    success=False,
                    error=str(e)
                ))
        
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
