# -*- coding: utf-8 -*-
"""
Agent Models - Agent领域模型
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.domain.agent.prompts import REACT_SYSTEM_PROMPT


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
    thought: str = ""           # 思考内容
    action: str = ""            # 行动名称
    action_input: Dict = field(default_factory=dict)  # 行动参数
    observation: str = ""       # 观察结果
    
    def to_message_content(self) -> List[Dict]:
        """转换为消息内容格式"""
        blocks = []
        
        # Thought 块
        if self.thought:
            blocks.append({
                "type": "thinking",
                "thinking": self.thought
            })
        
        # Action 块
        if self.action:
            blocks.append({
                "type": "tool_use",
                "id": f"action_{self.step_num}",
                "name": self.action,
                "input": self.action_input
            })
        
        return blocks


@dataclass
class AgentSession:
    """Agent 会话"""
    session_id: str
    gateway_key: str = ""
    llm_key: str = ""
    state: AgentState = AgentState.IDLE
    
    # ReAct 历史
    steps: List[ReActStep] = field(default_factory=list)
    current_step: Optional[ReActStep] = None
    
    # 消息历史 - 延迟导入避免循环依赖
    message_history: Optional[any] = field(default=None)
    
    # 统计
    total_steps: int = 0
    tools_called: List[str] = field(default_factory=list)
    
    # 累积内容
    accumulated_thinking: str = ""
    accumulated_text: str = ""
    
    def __post_init__(self):
        """初始化消息历史"""
        if self.message_history is None:
            from app.services.message_manager import MessageHistory
            self.message_history = MessageHistory(REACT_SYSTEM_PROMPT)
    
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
