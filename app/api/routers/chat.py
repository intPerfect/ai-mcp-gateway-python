# -*- coding: utf-8 -*-
"""
Chat Router - WebSocket对话路由
精简后的路由层，只负责WebSocket连接处理
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.api.schemas.chat import SessionRequest, SessionResponse
from app.domain.session.service import ws_session_manager, PendingSession
from app.services.react_agent import react_agent, AgentSession
from app.services.mcp_tool_registry import mcp_tool_registry
from app.services.conversation_logger import conversation_logger
from app.domain.protocol.websocket import WSEventFactory
from app.infrastructure.database import async_session_factory
from app.infrastructure.database.repository import McpGatewayRepository

logger = logging.getLogger(__name__)

router = APIRouter()


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
    
    # 必须选择至少一个微服务
    if not request.microservice_ids or len(request.microservice_ids) == 0:
        raise HTTPException(status_code=400, detail="请选择至少一个微服务")
    
    # 验证所选微服务是否有效
    if request.microservice_ids:
        async with async_session_factory() as session:
            repo = McpGatewayRepository(session)
            microservices = await repo.get_all_microservices()
            valid_ids = {ms.id for ms in microservices}
            invalid_ids = [mid for mid in request.microservice_ids if mid not in valid_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400, 
                    detail=f"无效的微服务ID: {invalid_ids}"
                )
    
    # 创建待连接会话
    session_id = ws_session_manager.create_pending_session(
        gateway_key=request.gateway_key,
        llm_key=request.llm_key,
        microservice_ids=request.microservice_ids
    )
    
    # 返回 WebSocket URL
    websocket_url = f"/ws/chat?session_id={session_id}"
    
    return SessionResponse(
        session_id=session_id,
        websocket_url=websocket_url,
        message="会话创建成功，请使用返回的 URL 连接 WebSocket"
    )


# ============ WebSocket 处理 ============

async def websocket_handler(websocket):
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
    pending = ws_session_manager.get_pending_session(session_id)
    if not pending:
        logger.warning(f"拒绝连接: 无效或已过期的 session_id: {session_id}")
        await websocket.close(code=4002, reason="Invalid or expired session_id")
        return
    
    gateway_key = pending.gateway_key
    llm_key = pending.llm_key
    microservice_ids = pending.microservice_ids
    logger.info(f"WebSocket 连接已接受：{session_id}, 微服务筛选: {microservice_ids}")
    
    # 确保工具已加载
    tool_count = len(mcp_tool_registry.get_tool_definitions())
    if tool_count == 0:
        logger.warning("工具未预加载，尝试加载...")
        try:
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
        # 获取带 microservice_name 的工具列表（根据选择的微服务筛选）
        tools_with_ms = await get_tools_with_microservice(microservice_ids)
        await websocket.send_json(
            WSEventFactory.welcome(session_id, tools_with_ms)
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


async def handle_chat_message(websocket, agent_session: AgentSession, msg: dict):
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


async def handle_clear_message(websocket, agent_session: AgentSession):
    """处理清空消息"""
    react_agent.clear_session(agent_session.session_id)
    await websocket.send_json(WSEventFactory.cleared())


# ============ 辅助函数 ============

async def load_tools_from_db(gateway_id: str = "gateway_001"):
    """从数据库加载工具"""
    async with async_session_factory() as session:
        result = await mcp_tool_registry.load_tools_from_db(session, gateway_id)
        return result


async def get_tools_with_microservice(microservice_ids: list = None) -> list:
    """
    获取带 microservice_name 的工具列表
    
    Args:
        microservice_ids: 可选，筛选指定微服务的工具。为 None 时返回所有工具
    """
    async with async_session_factory() as session:
        repo = McpGatewayRepository(session)
        all_tools = await repo.get_all_tools()
        enabled_tools = [t for t in all_tools if t.enabled == 1]
        all_microservices = await repo.get_all_microservices()
        ms_map = {ms.id: ms.name for ms in all_microservices}
        
        result = []
        for tool in enabled_tools:
            # 过滤：必须有微服务绑定
            if not tool.microservice_id or tool.microservice_id not in ms_map:
                continue
            
            # 如果指定了微服务筛选，只返回选中微服务的工具
            if microservice_ids and tool.microservice_id not in microservice_ids:
                continue
            
            tool_def = mcp_tool_registry.get_tool(tool.tool_name)
            if tool_def:
                result.append({
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "input_schema": tool_def.input_schema,
                    "microservice_name": ms_map[tool.microservice_id],
                })
        
        logger.info(f"加载工具: {len(result)} 个, 筛选微服务: {microservice_ids}")
        return result
