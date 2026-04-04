# -*- coding: utf-8 -*-
"""
ReAct Agent Service - 基于 ReAct 模型的智能代理

ReAct 模型核心循环：
1. Thought（思考）- 分析当前状态，规划下一步行动
2. Action（行动）- 选择并执行工具
3. Observation（观察）- 获取工具执行结果
4. 循环直到得出最终答案
"""

import asyncio
import json
import logging
import secrets
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.message_manager import MessageHistory, MessageBuilder
from app.services.conversation_logger import conversation_logger
from app.services.mcp_tool_registry import mcp_tool_registry
from app.services.llm_service import LLMService
from app.domain.protocol.websocket import WSEventFactory
from app.config import get_settings
from app.constants import REACT_SYSTEM_PROMPT
from app.domain.usage.service import get_usage_service
from app.utils.exceptions import RateLimitException
from app.infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentState(Enum):
    """Agent 状态"""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class ReActStep:
    """ReAct 单步记录"""

    step_num: int
    thought: str = ""  # 思考内容
    action: str = ""  # 行动名称
    action_input: Dict = field(default_factory=dict)  # 行动参数
    observation: str = ""  # 观察结果

    def to_message_content(self) -> List[Dict]:
        """转换为消息内容格式"""
        blocks = []

        # Thought 块
        if self.thought:
            blocks.append({"type": "thinking", "thinking": self.thought})

        # Action 块
        if self.action:
            blocks.append(
                {
                    "type": "tool_use",
                    "id": f"action_{self.step_num}",
                    "name": self.action,
                    "input": self.action_input,
                }
            )

        return blocks


@dataclass
class AgentSession:
    """Agent 会话"""

    session_id: str
    gateway_key: str = ""
    gateway_id: str = ""
    key_id: str = ""
    llm_key: str = ""
    llm_config_id: str = ""
    api_type: str = "anthropic"
    base_url: str = ""
    model_name: str = ""
    state: AgentState = AgentState.IDLE

    # ReAct 历史
    steps: List[ReActStep] = field(default_factory=list)
    current_step: Optional[ReActStep] = None

    # 消息历史
    message_history: MessageHistory = field(
        default_factory=lambda: MessageHistory(REACT_SYSTEM_PROMPT)
    )

    # 统计
    total_steps: int = 0
    tools_called: List[str] = field(default_factory=list)

    # 允许使用的工具名称列表（基于微服务筛选）
    allowed_tool_names: Optional[List[str]] = None

    # 累积内容
    accumulated_thinking: str = ""
    accumulated_text: str = ""

    def start_new_step(self) -> ReActStep:
        """开始新的一步"""
        self.total_steps += 1
        step = ReActStep(step_num=self.total_steps)
        self.current_step = step
        self.steps.append(step)
        return step

    def get_final_answer(self) -> str:
        """获取最终答案"""
        return self.accumulated_text


class ReActAgent:
    """ReAct Agent 服务"""

    MAX_STEPS = 15  # 最大步数限制

    def __init__(self):
        self.sessions: Dict[str, AgentSession] = {}

    def create_session(
        self,
        session_id: str,
        gateway_key: str = "",
        gateway_id: str = "",
        key_id: str = "",
        llm_key: str = "",
        llm_config_id: str = "",
        api_type: str = "anthropic",
        base_url: str = "",
        model_name: str = "",
        allowed_tool_names: Optional[List[str]] = None,
    ) -> AgentSession:
        """创建会话"""
        session = AgentSession(
            session_id=session_id,
            gateway_key=gateway_key,
            gateway_id=gateway_id,
            key_id=key_id,
            llm_key=llm_key,
            llm_config_id=llm_config_id,
            api_type=api_type,
            base_url=base_url,
            model_name=model_name,
            allowed_tool_names=allowed_tool_names,
        )
        self.sessions[session_id] = session
        logger.info(
            f"[ReAct] 创建会话: {session_id}, LLM配置: {llm_config_id}, API类型: {api_type}"
        )
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
        self, session_id: str, user_message: str
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
        self, session: AgentSession
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """ReAct 主循环"""

        # 创建会话级别的 LLMService，避免在循环中重复创建
        session_llm_service = LLMService(
            api_type=session.api_type,
            base_url=session.base_url,
            model_name=session.model_name,
        )

        while session.total_steps < self.MAX_STEPS:
            session.state = AgentState.THINKING

            # 开始新的一步
            step = session.start_new_step()
            logger.info(f"[ReAct] 步骤 {step.step_num} 开始")

            # 检查并增加使用计数（调用前检查）
            if session.gateway_id and session.key_id:
                try:
                    async with async_session_factory() as db_session:
                        usage_service = await get_usage_service(session=db_session)
                        await usage_service.check_and_increment(
                            gateway_id=session.gateway_id,
                            key_id=session.key_id,
                            call_type="llm",
                            call_detail=session.model_name,
                            session_id=session.session_id,
                        )
                except RateLimitException as e:
                    logger.warning(f"[ReAct] 使用限制: {e}")
                    yield WSEventFactory.error(str(e))
                    return
                except Exception as e:
                    logger.error(f"[ReAct] 检查使用限制失败: {e}")

            # 调用 LLM
            round_thinking = ""
            round_text = ""
            round_tool_calls = []

            # 记录请求
            await conversation_logger.log_llm_request(
                session.session_id,
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                round_num=step.step_num,
            )

            # 流式调用 LLM（使用会话特定的配置）
            async for llm_event in session_llm_service.chat_stream(
                session.message_history.get_messages_for_api(),
                tools_enabled=True,
                api_key=session.llm_key or None,
                allowed_names=session.allowed_tool_names,
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
                    yield WSEventFactory.thinking_delta(
                        thinking, round_thinking, step.step_num
                    )

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
                text=round_text, thinking=round_thinking, tool_calls=round_tool_calls
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
                    step.step_num,
                )
                break

            # 有行动，执行工具
            session.state = AgentState.ACTING
            logger.info(
                f"[ReAct] 步骤 {step.step_num} 执行 {len(round_tool_calls)} 个行动"
            )

            # 执行所有工具
            yield WSEventFactory.status(
                "executing_tools",
                f"执行 {len(round_tool_calls)} 个工具...",
                tool_calls=round_tool_calls,
            )

            tool_results = []

            # 并发执行工具 - 先发送所有 tool_call 事件
            for tool_call in round_tool_calls:
                tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("input", {})
                yield WSEventFactory.tool_call(
                    tool_id, tool_name, arguments, "executing"
                )

            # 定义单个工具执行函数
            async def execute_single_tool(
                tool_call: Dict,
            ) -> Tuple[str, str, Dict[str, Any], bool]:
                """执行单个工具，返回 (tool_id, tool_name, result, success)"""
                tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("input", {})

                try:
                    result = await mcp_tool_registry.execute_tool(tool_name, arguments)
                    return (tool_id, tool_name, result, True)
                except Exception as e:
                    error_result = {"error": str(e)}
                    return (tool_id, tool_name, error_result, False)

            # 并发执行所有工具
            tasks = [execute_single_tool(tc) for tc in round_tool_calls]
            execution_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果并发送事件
            for i, exec_result in enumerate(execution_results):
                tool_call = round_tool_calls[i]
                tool_id = tool_call.get("id", f"tool_{secrets.token_hex(8)}")
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("input", {})

                if isinstance(exec_result, Exception):
                    # 异常情况
                    error_result = {"error": str(exec_result)}
                    tool_results.append(
                        {
                            "tool_use_id": tool_id,
                            "tool_name": tool_name,
                            "result": error_result,
                            "success": False,
                        }
                    )
                    step.observation = f"Error: {str(exec_result)}"

                    await conversation_logger.log_tool_result(
                        session.session_id,
                        tool_id,
                        tool_name,
                        error_result,
                        False,
                        step.step_num,
                    )
                else:
                    # 正常结果
                    _, _, result, success = exec_result
                    tool_results.append(
                        {
                            "tool_use_id": tool_id,
                            "tool_name": tool_name,
                            "result": result,
                            "success": success,
                        }
                    )

                    if success:
                        step.observation = json.dumps(result, ensure_ascii=False)[:1000]
                        session.tools_called.append(tool_name)

                        # 记录工具调用使用量
                        if session.gateway_id and session.key_id:
                            try:
                                async with async_session_factory() as db_session:
                                    usage_service = await get_usage_service(
                                        session=db_session
                                    )
                                    await usage_service.check_and_increment(
                                        gateway_id=session.gateway_id,
                                        key_id=session.key_id,
                                        call_type="tool",
                                        call_detail=tool_name,
                                        session_id=session.session_id,
                                    )
                            except RateLimitException as e:
                                logger.warning(f"[ReAct] 工具调用超限: {e}")
                            except Exception as e:
                                logger.error(f"[ReAct] 记录工具使用量失败: {e}")

                        await conversation_logger.log_tool_call(
                            session.session_id,
                            tool_id,
                            tool_name,
                            arguments,
                            step.step_num,
                        )
                        await conversation_logger.log_tool_result(
                            session.session_id,
                            tool_id,
                            tool_name,
                            result,
                            True,
                            step.step_num,
                        )
                    else:
                        step.observation = (
                            f"Error: {result.get('error', 'Unknown error')}"
                        )

                        await conversation_logger.log_tool_result(
                            session.session_id,
                            tool_id,
                            tool_name,
                            result,
                            False,
                            step.step_num,
                        )

                # 发送 tool_result 事件
                yield WSEventFactory.tool_result(
                    tool_id,
                    tool_name,
                    tool_results[-1]["result"],
                    tool_results[-1]["success"],
                )

            # 将观察结果添加到消息历史
            session.state = AgentState.OBSERVING
            tool_result_blocks = []
            for tr in tool_results:
                tool_result_blocks.append(
                    {
                        "tool_use_id": tr["tool_use_id"],
                        "result": tr["result"],
                        "is_error": not tr["success"],
                    }
                )
            session.message_history.add_tool_results_batch(tool_result_blocks)

            yield WSEventFactory.status(
                "tools_completed", f"步骤 {step.step_num} 完成，继续思考..."
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
                session.total_steps,
            )
            event["limit_reached"] = True
            yield event

        # 记录会话结束
        await conversation_logger.log_session_end(
            session.session_id, session.total_steps, session.tools_called
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
