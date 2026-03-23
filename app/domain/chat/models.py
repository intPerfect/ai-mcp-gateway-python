# -*- coding: utf-8 -*-
"""
Chat Models - 对话领域模型
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


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


@dataclass
class ChatSession:
    """对话会话"""
    
    session_id: str
    gateway_key: str = ""
    llm_key: str = ""
    system_prompt: str = ""
    
    # 消息历史 - 延迟初始化
    message_history: Optional[any] = field(default=None)
    state: ChatState = ChatState.IDLE
    
    # 统计信息
    total_tool_rounds: int = 0
    tools_called: List[str] = field(default_factory=list)
    accumulated_thinking: str = ""  # 累积的思考内容
    accumulated_text: str = ""  # 累积的文本内容
    
    def __post_init__(self):
        """初始化消息历史"""
        if self.message_history is None:
            from app.domain.chat.history import MessageHistory, DEFAULT_SYSTEM_PROMPT
            self.message_history = MessageHistory(self.system_prompt or DEFAULT_SYSTEM_PROMPT)
    
    def reset_for_new_turn(self):
        """为新一轮对话重置累积内容（但保留历史）"""
        self.accumulated_thinking = ""
        self.accumulated_text = ""
        self.state = ChatState.IDLE
