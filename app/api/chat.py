# -*- coding: utf-8 -*-
"""
WebSocket Chat API - 对话接口 (ReAct Agent 版)
基于 ReAct 模型的智能代理，实现 Thought-Action-Observation 循环
"""

import json
import logging
import secrets
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.services.react_agent import react_agent, AgentSession
from app.services.mcp_tool_registry import mcp_tool_registry
from app.services.conversation_logger import conversation_logger
from app.services.websocket_protocol import WSEventFactory
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 创建路由
router = APIRouter()


# ============ 请求/响应模型 ============

class SessionRequest(BaseModel):
    """WebSocket 会话请求"""
    gateway_key: str
    llm_key: str


class SessionResponse(BaseModel):
    """WebSocket 会话响应"""
    session_id: str
    websocket_url: str
    message: str


class PendingSession:
    """待连接的会话信息"""
    def __init__(self, gateway_key: str, llm_key: str):
        self.gateway_key = gateway_key
        self.llm_key = llm_key


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.pending_sessions: Dict[str, PendingSession] = {}
    
    def create_pending_session(self, gateway_key: str, llm_key: str) -> str:
        """创建待连接的会话"""
        session_id = f"session_{secrets.token_hex(16)}"
        self.pending_sessions[session_id] = PendingSession(gateway_key, llm_key)
        logger.info(f"创建待连接会话: {session_id}")
        return session_id
    
    def get_pending_session(self, session_id: str) -> Optional[PendingSession]:
        """获取并移除待连接会话"""
        return self.pending_sessions.pop(session_id, None)


# 全局会话管理器
session_manager = SessionManager()


# ============ HTTP 接口 ============

@router.post("/session", response_model=SessionResponse)
async def create_chat_session(request: SessionRequest):
    """
    创建对话会话
    
    验证 gateway_key 和 llm_key，验证成功后返回 WebSocket 连接 URL
    """
    # 验证 gateway_key
    if not request.gateway_key:
        raise HTTPException(status_code=400, detail="网关 API Key 不能为空")
    
    # 验证 llm_key
    if not request.llm_key:
        raise HTTPException(status_code=400, detail="LLM API Key 不能为空")
    
    # 创建待连接会话
    session_id = session_manager.create_pending_session(
        gateway_key=request.gateway_key,
        llm_key=request.llm_key
    )
    
    # 返回 WebSocket URL
    websocket_url = f"/ws/chat?session_id={session_id}"
    
    return SessionResponse(
        session_id=session_id,
        websocket_url=websocket_url,
        message="会话创建成功，请使用返回的 URL 连接 WebSocket"
    )


# ============ WebSocket 处理 ============

async def websocket_handler(websocket: WebSocket):
    """WebSocket 对话处理"""
    session_id = websocket.query_params.get("session_id", "")
    
    # 先接受连接
    try:
        await websocket.accept()
    except Exception as e:
        logger.error(f"接受 WebSocket 连接失败：{e}")
        return
    
    # 验证 session_id
    if not session_id:
        logger.warning("拒绝连接: 缺少 session_id")
        await websocket.close(code=4001, reason="Missing session_id")
        return
    
    # 获取待连接会话信息
    pending = session_manager.get_pending_session(session_id)
    if not pending:
        logger.warning(f"拒绝连接: 无效或已过期的 session_id: {session_id}")
        await websocket.close(code=4002, reason="Invalid or expired session_id")
        return
    
    gateway_key = pending.gateway_key
    llm_key = pending.llm_key
    logger.info(f"WebSocket 连接已接受：{session_id}")
    
    # 确保工具已加载
    tool_count = len(mcp_tool_registry.get_tool_definitions())
    if tool_count == 0:
        logger.warning("工具未预加载，尝试加载...")
        try:
            from app.infrastructure.database import async_session_factory
            async with async_session_factory() as session:
                result = await mcp_tool_registry.load_tools_from_db(session, "gateway_001")
                tool_count = len(result.get("registered", []))
                logger.info(f"工具已加载: {tool_count} 个")
        except Exception as e:
            logger.error(f"加载工具失败: {e}")
    
    # 创建 ReAct Agent 会话
    agent_session = react_agent.create_session(
        session_id=session_id,
        gateway_key=gateway_key,
        llm_key=llm_key
    )
    
    # 记录会话开始
    await conversation_logger.log_session_start(
        session_id,
        gateway_key[:10] + "..." if gateway_key else "",
        llm_key[:10] + "..." if llm_key else ""
    )
    
    try:
        # 发送欢迎消息
        await websocket.send_json(
            WSEventFactory.welcome(session_id, mcp_tool_registry.get_tool_definitions())
        )
        
        # 主消息循环
        while True:
            data = await websocket.receive_text()
            logger.debug(f"收到消息: {data[:100]}...")
            
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "chat":
                    await handle_chat_message(websocket, agent_session, msg)
                
                elif msg_type == "clear":
                    await handle_clear_message(websocket, agent_session)
                
                elif msg_type == "ping":
                    await websocket.send_json(WSEventFactory.pong())
                
            except json.JSONDecodeError:
                await websocket.send_json(WSEventFactory.error("无效的JSON格式"))
            except Exception as e:
                logger.error(f"处理消息异常: {e}", exc_info=True)
                await websocket.send_json(WSEventFactory.error(str(e)))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket异常: {e}", exc_info=True)
    finally:
        # 清理
        react_agent.remove_session(session_id)


async def handle_chat_message(websocket: WebSocket, agent_session: AgentSession, msg: dict):
    """处理聊天消息 - ReAct 模式"""
    user_message = msg.get("content", "")
    if not user_message:
        return
    
    logger.info(f"[{agent_session.session_id}] 用户消息: {user_message[:50]}...")
    
    # 发送处理中状态
    await websocket.send_json(WSEventFactory.status("thinking", "ReAct 思考中..."))
    
    # 运行 ReAct 循环
    async for event in react_agent.run(agent_session.session_id, user_message):
        await websocket.send_json(event)


async def handle_clear_message(websocket: WebSocket, agent_session: AgentSession):
    """处理清空消息"""
    react_agent.clear_session(agent_session.session_id)
    await websocket.send_json(WSEventFactory.cleared())


# ============ 辅助函数 ============

async def load_tools_from_db(gateway_id: str = "gateway_001"):
    """从数据库加载工具"""
    from app.infrastructure.database import async_session_factory
    async with async_session_factory() as session:
        result = await mcp_tool_registry.load_tools_from_db(session, gateway_id)
        return result