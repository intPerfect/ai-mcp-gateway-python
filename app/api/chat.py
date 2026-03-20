# -*- coding: utf-8 -*-
"""
WebSocket Chat API - 对话接口 (Anthropic API)
"""
import json
import logging
import secrets
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.services.llm_service import llm_service
from app.services.mcp_tool_registry import mcp_tool_registry
from app.config import get_settings
from app.infrastructure.database import get_db_session, async_session_factory

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


class ChatSession:
    """对话会话"""
    
    def __init__(self, session_id: str, gateway_key: str = "", llm_key: str = "", tools_loaded: bool = False):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.gateway_key = gateway_key  # 网关认证Key
        self.llm_key = llm_key         # LLM API调用Key
        self.tools_loaded = tools_loaded
    
    def add_message(self, role: str, content):
        self.messages.append({"role": role, "content": content})
    
    def get_history(self) -> List[Dict[str, str]]:
        return self.messages.copy()


class ChatManager:
    """对话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.pending_sessions: Dict[str, dict] = {}  # 待连接的已验证会话
    
    async def load_tools_from_db(self, gateway_id: str = "gateway_001"):
        """从数据库加载工具"""
        from app.infrastructure.database import async_session_factory
        async with async_session_factory() as session:
            result = await mcp_tool_registry.load_tools_from_db(session, gateway_id)
            logger.info(f"从数据库加载工具: {result}")
            return result
    
    def create_pending_session(self, gateway_key: str, llm_key: str) -> str:
        """创建待连接的已验证会话"""
        session_id = f"session_{secrets.token_hex(16)}"
        self.pending_sessions[session_id] = {
            "gateway_key": gateway_key,
            "llm_key": llm_key
        }
        logger.info(f"创建待连接会话: {session_id}")
        return session_id
    
    def get_pending_session(self, session_id: str) -> Optional[dict]:
        """获取待连接会话"""
        return self.pending_sessions.get(session_id)
    
    def consume_pending_session(self, session_id: str) -> Optional[dict]:
        """消费待连接会话（获取后删除）"""
        return self.pending_sessions.pop(session_id, None)
    
    def create_session(self, session_id: str, gateway_key: str = "", llm_key: str = "", tools_loaded: bool = False) -> ChatSession:
        """创建会话"""
        session = ChatSession(session_id, gateway_key, llm_key, tools_loaded)
        self.sessions[session_id] = session
        
        # 添加系统提示
        session.add_message("system", "你是一个智能助手。当用户提问时，你可以调用工具来获取信息。")
        
        logger.info(f"创建对话会话: {session_id}, llm_key: {llm_key[:20] if llm_key else 'None'}...")
        return session
    
    def get_session(self, session_id: str) -> ChatSession:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"删除对话会话: {session_id}")


# 全局对话管理器
chat_manager = ChatManager()


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
    
    # TODO: 这里可以添加更严格的 Key 验证逻辑
    # 例如：从数据库验证 gateway_key，调用 LLM API 验证 llm_key
    
    # 创建待连接会话
    session_id = chat_manager.create_pending_session(
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


async def websocket_handler(websocket: WebSocket):
    """WebSocket 对话处理"""
    session_id = websocket.query_params.get("session_id", "")
    
    # 先接受连接，再验证（必须先 accept 才能发送关闭帧，否则 uvicorn 会返回 HTTP 403）
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

    # 从待连接会话中获取已验证的信息
    pending = chat_manager.consume_pending_session(session_id)
    if not pending:
        logger.warning(f"拒绝连接: 无效或已过期的 session_id: {session_id}")
        await websocket.close(code=4002, reason="Invalid or expired session_id")
        return

    gateway_key = pending.get("gateway_key", "")
    llm_key = pending.get("llm_key", "")
    logger.info(f"WebSocket 连接已接受：{session_id}")
        
    # 检查工具是否已加载
    tools_loaded = len(mcp_tool_registry.get_tool_definitions()) > 0
        
    # 如果工具未加载，从数据库加载
    if not tools_loaded:
        try:
            await chat_manager.load_tools_from_db()
            tools_loaded = True
            logger.info("工具已从数据库加载")
        except Exception as e:
            logger.error(f"加载工具失败：{str(e)}")
        
    # 创建或获取会话
    session = chat_manager.get_session(session_id)
    if not session:
        session = chat_manager.create_session(session_id, gateway_key, llm_key, tools_loaded)
        
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "session_id": session_id,
            "tools": mcp_tool_registry.get_tool_definitions()
        })
        logger.info(f"已发送欢迎消息到会话：{session_id}")
        
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info(f"收到消息: {data[:100]}...")
            
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "chat":
                    user_message = msg.get("content", "")
                    
                    # 添加用户消息
                    session.add_message("user", user_message)
                    
                    # 发送处理中状态
                    await websocket.send_json({
                        "type": "status",
                        "status": "thinking",
                        "message": "正在思考..."
                    })
                    
                    # 流式调用LLM
                    accumulated_text = ""
                    content_blocks = []
                    tool_calls = []
                    
                    async for event in llm_service.chat_stream(
                        session.get_history(),
                        tools_enabled=True,
                        api_key=session.llm_key or None
                    ):
                        event_type = event.get("type")
                        
                        if event_type == "stream_start":
                            await websocket.send_json({
                                "type": "stream_start"
                            })
                        
                        elif event_type == "text_delta":
                            text = event.get("text", "")
                            accumulated_text += text
                            await websocket.send_json({
                                "type": "text_delta",
                                "text": text
                            })
                        
                        elif event_type == "text_stop":
                            await websocket.send_json({
                                "type": "text_stop",
                                "text": accumulated_text
                            })
                        
                        elif event_type == "tool_use_start":
                            await websocket.send_json({
                                "type": "tool_use_start",
                                "id": event.get("id"),
                                "name": event.get("name")
                            })
                        
                        elif event_type == "tool_use_stop":
                            await websocket.send_json({
                                "type": "tool_use_stop"
                            })
                        
                        elif event_type == "stream_end":
                            content_blocks = event.get("content_blocks", [])
                            tool_calls = event.get("tool_calls", [])
                        
                        elif event_type == "error":
                            await websocket.send_json({
                                "type": "error",
                                "message": event.get("error", "未知错误")
                            })
                            break
                    
                    # 处理工具调用
                    if tool_calls:
                        # 将assistant响应块添加到消息历史
                        if content_blocks:
                            session.add_message("assistant", content_blocks)
                        
                        # 执行工具调用
                        tool_results = []
                        
                        for tool_call in tool_calls:
                            tool_use_id = tool_call.get("id", "")
                            tool_name = tool_call.get("name")
                            arguments = tool_call.get("input", {})
                            
                            logger.info(f"执行工具: {tool_name}, 参数: {arguments}")
                            
                            # 发送工具调用状态
                            await websocket.send_json({
                                "type": "tool_call",
                                "tool": tool_name,
                                "arguments": arguments,
                                "status": "executing"
                            })
                            
                            # 执行工具
                            result = await llm_service.execute_tool(tool_name, arguments)
                            tool_results.append({
                                "tool_use_id": tool_use_id,
                                "tool": tool_name,
                                "result": result
                            })
                            
                            # 发送工具结果
                            await websocket.send_json({
                                "type": "tool_result",
                                "tool": tool_name,
                                "result": result
                            })
                        
                        # 添加工具结果到上下文（tool_result 必须用 user 角色，符合 Anthropic API 规范）
                        tool_result_blocks = []
                        for tr in tool_results:
                            tool_use_id = tr["tool_use_id"]
                            result_json = json.dumps(tr["result"], ensure_ascii=False)
                            tool_result_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result_json
                            })
                        session.add_message("user", tool_result_blocks)
                        
                        # 流式调用LLM生成最终回答
                        await websocket.send_json({
                            "type": "status",
                            "status": "thinking",
                            "message": "整合工具结果..."
                        })
                        
                        final_text = ""
                        final_content_blocks = []
                        
                        async for event in llm_service.chat_stream(
                            session.get_history(),
                            tools_enabled=False,
                            api_key=session.llm_key or None
                        ):
                            event_type = event.get("type")
                            
                            if event_type == "stream_start":
                                await websocket.send_json({
                                    "type": "stream_start"
                                })
                            
                            elif event_type == "text_delta":
                                text = event.get("text", "")
                                final_text += text
                                await websocket.send_json({
                                    "type": "text_delta",
                                    "text": text
                                })
                            
                            elif event_type == "text_stop":
                                await websocket.send_json({
                                    "type": "text_stop",
                                    "text": final_text
                                })
                            
                            elif event_type == "stream_end":
                                final_content_blocks = event.get("content_blocks", [])
                            
                            elif event_type == "error":
                                await websocket.send_json({
                                    "type": "error",
                                    "message": event.get("error", "未知错误")
                                })
                                break
                        
                        # 保存到会话历史
                        if final_content_blocks:
                            session.add_message("assistant", final_content_blocks)
                        else:
                            session.add_message("assistant", final_text)
                        
                        # 发送完成消息
                        await websocket.send_json({
                            "type": "response",
                            "content": final_text,
                            "tool_calls": [tr["tool"] for tr in tool_results]
                        })
                    else:
                        # 无工具调用，直接返回回答
                        if accumulated_text:
                            session.add_message("assistant", accumulated_text)
                            await websocket.send_json({
                                "type": "response",
                                "content": accumulated_text
                            })
                        elif not content_blocks:
                            await websocket.send_json({
                                "type": "error",
                                "message": "未获取到有效回答"
                            })
                
                elif msg_type == "clear":
                    # 清空会话
                    session.messages = []
                    session.add_message("system", "你是一个智能助手。当用户提问时，你可以调用工具来获取信息。")
                    await websocket.send_json({
                        "type": "status",
                        "status": "cleared",
                        "message": "对话已清空"
                    })
                
                elif msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "无效的JSON格式"
                })
            except Exception as e:
                logger.error(f"处理消息异常: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket异常: {str(e)}")
    finally:
        chat_manager.remove_session(session_id)
