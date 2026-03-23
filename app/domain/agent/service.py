# -*- coding: utf-8 -*-
"""
Agent Service - Agent领域服务
ReAct Agent 核心逻辑
"""
import json
import logging
import secrets
from typing import Any, Dict, List, Optional, AsyncGenerator

from app.domain.agent.models import AgentSession, AgentState, ReActStep
from app.services.message_manager import MessageBuilder
from app.services.conversation_logger import conversation_logger
from app.services.llm_service import llm_service
from app.services.websocket_protocol import WSEventFactory

logger = logging.getLogger(__name__)


class ReActAgent:
    """ReAct Agent 服务"""
    
    MAX_STEPS = 15  # 最大步数限制
    
    def __init__(self):
        self.sessions: Dict[str, AgentSession] = {}
    
    def create_session(
        self,
        session_id: str,
        gateway_key: str = "",
        llm_key: str = ""
    ) -> AgentSession:
        """创建会话"""
        session = AgentSession(
            session_id=session_id,
            gateway_key=gateway_key,
            llm_key=llm_key
        )
        self.sessions[session_id] = session
        logger.info(f"[ReAct] 创建会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[ReAct] 移除会话: {session_id}")
    
    async def run(
        self,
        session_id: str,
        user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行 ReAct 循环
        
        核心流程：
        1. 接收用户输入
        2. LLM 思考 + 可能的行动
        3. 如果有行动，执行工具
        4. 将观察结果反馈给 LLM
        5. 重复 2-4 直到 LLM 给出最终答案
        """
        session = self.sessions.get(session_id)
        if not session:
            yield WSEventFactory.error("会话不存在")
            return
        
        try:
            session.state = AgentState.THINKING
            
            # 记录用户输入
            await conversation_logger.log_user_input(session_id, user_message)
            session.message_history.add_user_message(user_message)
            
            # 发送流开始
            yield WSEventFactory.stream_start()
            
            # ReAct 主循环
            async for event in self._react_loop(session):
                yield event
                
        except Exception as e:
            logger.error(f"[ReAct] 运行异常: {e}", exc_info=True)
            yield WSEventFactory.error(str(e))
        finally:
            session.state = AgentState.IDLE
    
    async def _react_loop(
        self, 
        session: AgentSession
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """ReAct 主循环"""
        
        while session.total_steps < self.MAX_STEPS:
            session.state = AgentState.THINKING
            
            # 开始新的一步
            step = session.start_new_step()
            logger.info(f"[ReAct] 步骤 {step.step_num} 开始")
            
            # 调用 LLM
            round_thinking = ""
            round_text = ""
            round_tool_calls = []
            
            # 记录请求
            await conversation_logger.log_llm_request(
                session.session_id,
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                round_num=step.step_num
            )
            
            # 流式调用 LLM
            async for llm_event in llm_service.chat_stream(
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                api_key=session.llm_key or None
            ):
                event_type = llm_event.get("type")
                
                if event_type == "text_delta":
                    text = llm_event.get("text", "")
                    round_text += text
                    yield WSEventFactory.text_delta(text)
                
                elif event_type == "thinking_delta":
                    thinking = llm_event.get("thinking", "")
                    round_thinking += thinking
                    session.accumulated_thinking += thinking
                    await conversation_logger.log_llm_thinking(
                        session.session_id, thinking, step.step_num
                    )
                    yield WSEventFactory.thinking_delta(thinking, round_thinking, step.step_num)
                
                elif event_type == "tool_use_start":
                    tool_id = llm_event.get("id", "")
                    tool_name = llm_event.get("name", "")
                    yield WSEventFactory.tool_use_start(tool_id, tool_name)
                
                elif event_type == "tool_use_stop":
                    yield WSEventFactory.tool_use_stop()
                
                elif event_type == "stream_end":
                    round_tool_calls = llm_event.get("tool_calls", [])
                    
                    # 从 content_blocks 获取文本
                    content_blocks = llm_event.get("content_blocks", [])
                    if content_blocks:
                        for block in content_blocks:
                            if block.get("type") == "text":
                                round_text = block.get("text", "")
                                break
                
                elif event_type == "error":
                    yield WSEventFactory.error(llm_event.get("error", "未知错误"))
                    return
            
            # 记录思考
            step.thought = round_thinking
            
            # 保存 assistant 响应
            assistant_blocks = MessageBuilder.build_assistant_response(
                text=round_text,
                thinking=round_thinking,
                tool_calls=round_tool_calls
            )
            if assistant_blocks:
                session.message_history.add_assistant_message(assistant_blocks)
            
            # 记录响应
            await conversation_logger.log_llm_response(
                session.session_id, round_text, round_tool_calls, step.step_num
            )
            
            # 检查是否有行动
            if not round_tool_calls:
                # 没有行动，对话结束
                logger.info(f"[ReAct] 步骤 {step.step_num} 无行动，结束")
                
                final_text = round_text or session.accumulated_text
                if final_text:
                    session.accumulated_text = final_text
                
                yield WSEventFactory.response(
                    final_text or "任务完成",
                    session.accumulated_thinking,
                    session.tools_called,
                    step.step_num
                )
                break
            
            # 有行动，执行工具
            session.state = AgentState.ACTING
            logger.info(f"[ReAct] 步骤 {step.step_num} 执行 {len(round_tool_calls)} 个行动")
            
            # 执行所有工具
            yield WSEventFactory.status(
                "executing_tools",
                f"执行 {len(round_tool_calls)} 个工具...",
                tool_calls=round_tool_calls
            )
            
            tool_results = []
            for tool_call in round_tool_calls:
                tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("input", {})
                
                step.action = tool_name
                step.action_input = arguments
                
                yield WSEventFactory.tool_call(tool_id, tool_name, arguments, "executing")
                
                # 执行工具
                try:
                    result = await llm_service.execute_tool(tool_name, arguments)
                    tool_results.append({
                        "tool_use_id": tool_id,
                        "tool_name": tool_name,
                        "result": result,
                        "success": True
                    })
                    step.observation = json.dumps(result, ensure_ascii=False)[:1000]
                    session.tools_called.append(tool_name)
                    
                    await conversation_logger.log_tool_call(
                        session.session_id, tool_id, tool_name, arguments, step.step_num
                    )
                    await conversation_logger.log_tool_result(
                        session.session_id, tool_id, tool_name, result, True, step.step_num
                    )
                    
                except Exception as e:
                    error_result = {"error": str(e)}
                    tool_results.append({
                        "tool_use_id": tool_id,
                        "tool_name": tool_name,
                        "result": error_result,
                        "success": False
                    })
                    step.observation = f"Error: {str(e)}"
                    
                    await conversation_logger.log_tool_result(
                        session.session_id, tool_id, tool_name, error_result, False, step.step_num
                    )
                
                yield WSEventFactory.tool_result(
                    tool_id, tool_name, 
                    tool_results[-1]["result"],
                    tool_results[-1]["success"]
                )
            
            # 将观察结果添加到消息历史
            session.state = AgentState.OBSERVING
            tool_result_blocks = []
            for tr in tool_results:
                tool_result_blocks.append({
                    "tool_use_id": tr["tool_use_id"],
                    "result": tr["result"],
                    "is_error": not tr["success"]
                })
            session.message_history.add_tool_results_batch(tool_result_blocks)
            
            yield WSEventFactory.status(
                "tools_completed",
                f"步骤 {step.step_num} 完成，继续思考..."
            )

            # 工具执行完毕后，通知前端准备接收下一轮流式输出
            yield WSEventFactory.stream_start()

            # 继续下一轮循环...
        
        else:
            # 达到最大步数
            logger.warning(f"[ReAct] 达到最大步数 {self.MAX_STEPS}")
            event = WSEventFactory.response(
                "我已执行了多步操作，达到了处理上限。如需继续，请告诉我。",
                session.accumulated_thinking,
                session.tools_called,
                session.total_steps
            )
            event["limit_reached"] = True
            yield event
        
        # 记录会话结束
        await conversation_logger.log_session_end(
            session.session_id,
            session.total_steps,
            session.tools_called
        )
    
    def clear_session(self, session_id: str):
        """清空会话"""
        session = self.sessions.get(session_id)
        if session:
            session.message_history.clear(keep_system=True)
            session.steps = []
            session.current_step = None
            session.total_steps = 0
            session.tools_called = []
            session.accumulated_thinking = ""
            session.accumulated_text = ""
            logger.info(f"[ReAct] 清空会话: {session_id}")


# 全局单例
react_agent = ReActAgent()
