# -*- coding: utf-8 -*-
"""
ReAct Service - ReAct应用服务
基于ReAct模式的智能代理服务
"""
import logging
from typing import Dict, Optional

from app.domain.agent.models import AgentSession
from app.domain.agent.service import ReActAgent

logger = logging.getLogger(__name__)


class ReActService:
    """ReAct应用服务 - 封装ReActAgent"""
    
    def __init__(self):
        self._agent = ReActAgent()
    
    def create_session(
        self,
        session_id: str,
        gateway_key: str = "",
        llm_key: str = ""
    ) -> AgentSession:
        """创建会话"""
        return self._agent.create_session(session_id, gateway_key, llm_key)
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """获取会话"""
        return self._agent.get_session(session_id)
    
    def remove_session(self, session_id: str):
        """移除会话"""
        self._agent.remove_session(session_id)
    
    def run(self, session_id: str, user_message: str):
        """运行ReAct循环"""
        return self._agent.run(session_id, user_message)
    
    def clear_session(self, session_id: str):
        """清空会话"""
        self._agent.clear_session(session_id)


# 全局单例
react_service = ReActService()
