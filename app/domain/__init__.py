# -*- coding: utf-8 -*-
"""
Domain Layer - 领域层
"""
from app.domain.auth import AuthService, LicenseCommand, RateLimitCommand
from app.domain.session import (
    session_manager,
    ws_session_manager,
    MessageHandler,
    SessionConfig,
    PendingSession
)
from app.domain.protocol import HttpGateway, WSEventType, WSEventFactory
from app.domain.agent import AgentSession, AgentState, ReActAgent, REACT_SYSTEM_PROMPT
from app.domain.tool import ToolDefinition, ToolStatus, McpToolRegistry
from app.domain.chat import ChatSession, ChatState, MessageHistory, MessageBuilder

__all__ = [
    # Auth
    "AuthService", "LicenseCommand", "RateLimitCommand",
    # Session
    "session_manager", "ws_session_manager", "MessageHandler", "SessionConfig", "PendingSession",
    # Protocol
    "HttpGateway", "WSEventType", "WSEventFactory",
    # Agent
    "AgentSession", "AgentState", "ReActAgent", "REACT_SYSTEM_PROMPT",
    # Tool
    "ToolDefinition", "ToolStatus", "McpToolRegistry",
    # Chat
    "ChatSession", "ChatState", "MessageHistory", "MessageBuilder"
]
