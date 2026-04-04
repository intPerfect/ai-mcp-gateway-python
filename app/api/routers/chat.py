# -*- coding: utf-8 -*-
"""
Chat Router - WebSocket对话路由
精简后的路由层，只负责WebSocket连接处理
"""

import json
import logging
from typing import Optional, List
from fastapi import APIRouter, WebSocketDisconnect, HTTPException, Body
from pydantic import BaseModel

from app.api.schemas.chat import (
    SessionRequest,
    SessionResponse,
    GatewayVerifyResponse,
    MicroserviceInfo,
    LlmConfigInfo,
)
from app.domain.session.service import ws_session_manager
from app.services.react_agent import react_agent, AgentSession
from app.services.mcp_tool_registry import mcp_tool_registry
from app.services.conversation_logger import conversation_logger
from app.domain.protocol.websocket import WSEventFactory
from app.infrastructure.database import async_session_factory
from app.infrastructure.database.repositories import (
    AuthRepository, GatewayRepository, MicroserviceRepository,
    LlmConfigRepository,
)
from app.utils.security import parse_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ HTTP 接口 ============


@router.post("/verify", response_model=GatewayVerifyResponse)
async def verify_gateway_key(gateway_key: str = Body(..., media_type="text/plain")):
    """
    验证网关API Key并返回网关信息及绑定的微服务列表和LLM配置列表
    """
    if not gateway_key:
        raise HTTPException(status_code=400, detail="网关 API Key 不能为空")

    async with async_session_factory() as session:
        auth_repo = AuthRepository(session)
        gw_repo = GatewayRepository(session)
        ms_repo = MicroserviceRepository(session)
        llm_repo = LlmConfigRepository(session)

        # 验证 gateway_key 并获取 gateway_id
        gateway_id = await auth_repo.get_gateway_id_by_api_key(gateway_key)
        if not gateway_id:
            raise HTTPException(status_code=401, detail="无效的网关 API Key")

        # 获取网关信息
        gateway = await gw_repo.get_gateway_by_id(gateway_id)
        if not gateway:
            raise HTTPException(status_code=404, detail="网关不存在")

        # 获取绑定的微服务ID列表
        bound_ms = await gw_repo.get_gateway_microservices(gateway_id)
        bound_ms_ids = [bm.microservice_id for bm in bound_ms]

        # 获取微服务详情
        microservices = []
        for ms_id in bound_ms_ids:
            ms = await ms_repo.get_microservice_by_id(ms_id)
            if ms:
                business_line_name = None
                if ms.business_line_id:
                    from app.infrastructure.database.models import SysBusinessLine
                    bl = await session.get(SysBusinessLine, ms.business_line_id)
                    business_line_name = bl.line_name if bl else None
                microservices.append(
                    MicroserviceInfo(
                        id=ms.id,
                        name=ms.name,
                        health_status=ms.health_status or "unknown",
                        business_line=business_line_name,
                    )
                )

        # 获取网关绑定的LLM配置列表
        llm_configs = await llm_repo.get_gateway_llm_configs(gateway_id)
        llm_config_infos = [
            LlmConfigInfo(
                config_id=lc.config_id,
                config_name=lc.config_name,
                api_type=lc.api_type,
                model_name=lc.model_name,
                description=lc.description,
            )
            for lc in llm_configs
        ]

        return GatewayVerifyResponse(
            gateway_id=gateway.gateway_id,
            gateway_name=gateway.gateway_name,
            gateway_desc=gateway.gateway_desc,
            microservices=microservices,
            llm_configs=llm_config_infos,
        )


class LLMTestResponse(BaseModel):
    success: bool
    message: str
    reply: Optional[str] = None


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm_config(llm_config_id: str = Body(..., media_type="text/plain")):
    """
    测试LLM配置是否有效
    """
    if not llm_config_id:
        raise HTTPException(status_code=400, detail="LLM配置ID不能为空")

    async with async_session_factory() as session:
        llm_repo = LlmConfigRepository(session)
        llm_config = await llm_repo.get_llm_config_by_config_id(llm_config_id)

        if not llm_config:
            raise HTTPException(status_code=404, detail="LLM配置不存在")

        from app.services.llm.base import LLMService

        llm_service = LLMService(
            api_type=llm_config.api_type,
            base_url=llm_config.base_url,
            model_name=llm_config.model_name,
        )
        try:
            result = await llm_service.chat(
                messages=[{"role": "user", "content": "你好"}],
                tools_enabled=False,
                api_key=llm_config.api_key,
            )

            if "error" in result:
                return LLMTestResponse(
                    success=False,
                    message="LLM配置无效或调用失败",
                    reply=result.get("error"),
                )

            content = result.get("content_blocks", [])
            reply_text = ""
            for block in content:
                if block.get("type") == "text":
                    reply_text = block.get("text", "")

            return LLMTestResponse(
                success=True,
                message="LLM配置验证成功",
                reply=reply_text,
            )
        except Exception as e:
            logger.error(f"LLM 测试失败: {str(e)}")
            return LLMTestResponse(
                success=False,
                message=f"LLM 调用失败: {str(e)}",
                reply=None,
            )


@router.post("/session", response_model=SessionResponse)
async def create_chat_session(request: SessionRequest):
    """
    创建对话会话

    验证 gateway_key 和 llm_config_id，验证成功后返回 WebSocket 连接 URL
    """
    # 验证 gateway_key
    if not request.gateway_key:
        raise HTTPException(status_code=400, detail="网关 API Key 不能为空")

    # 验证 llm_config_id
    if not request.llm_config_id:
        raise HTTPException(status_code=400, detail="LLM配置ID不能为空")

    # 必须选择至少一个微服务
    if not request.microservice_ids or len(request.microservice_ids) == 0:
        raise HTTPException(status_code=400, detail="请选择至少一个微服务")

    # 验证 gateway_key 是否有效，并获取 gateway_id
    async with async_session_factory() as session:
        auth_repo = AuthRepository(session)
        llm_repo = LlmConfigRepository(session)
        gw_repo = GatewayRepository(session)
        gateway_id = await auth_repo.get_gateway_id_by_api_key(request.gateway_key)
        if not gateway_id:
            raise HTTPException(status_code=401, detail="无效的网关 API Key")
    
        # 验证 LLM配置是否存在并绑定到该网关
        is_bound = await llm_repo.is_llm_bound_to_gateway(gateway_id, request.llm_config_id)
        if not is_bound:
            raise HTTPException(
                status_code=403,
                detail="该LLM配置未绑定到此网关",
            )
    
        # 获取LLM配置
        llm_config = await llm_repo.get_llm_config_by_config_id(request.llm_config_id)
        if not llm_config:
            raise HTTPException(status_code=404, detail="LLM配置不存在")
    
        # 获取网关绑定的微服务列表
        bound_microservices = await gw_repo.get_gateway_microservices(gateway_id)
        bound_ms_ids = {bm.microservice_id for bm in bound_microservices}

        # 验证所选微服务是否都在该网关上（权限隔离）
        invalid_ids = [
            mid for mid in request.microservice_ids if mid not in bound_ms_ids
        ]
        if invalid_ids:
            raise HTTPException(
                status_code=403,
                detail=f"以下微服务未绑定到此网关: {invalid_ids}，请选择网关绑定的微服务",
            )

    # 创建待连接会话（使用LLM配置信息）
    session_id = ws_session_manager.create_pending_session(
        gateway_key=request.gateway_key,
        llm_key=llm_config.api_key,
        microservice_ids=request.microservice_ids,
        llm_config_id=request.llm_config_id,
        api_type=llm_config.api_type,
        base_url=llm_config.base_url,
        model_name=llm_config.model_name,
    )

    # 返回 WebSocket URL
    websocket_url = f"/ws/chat?session_id={session_id}"

    return SessionResponse(
        session_id=session_id,
        websocket_url=websocket_url,
        message="会话创建成功，请使用返回的 URL 连接 WebSocket",
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
    llm_config_id = pending.llm_config_id
    api_type = pending.api_type
    base_url = pending.base_url
    model_name = pending.model_name

    # 解析 gateway_key 获取 key_id
    key_id = parse_api_key(gateway_key) if gateway_key else None

    # 获取 gateway_id
    gateway_id = None
    if gateway_key:
        async with async_session_factory() as session:
            auth_repo = AuthRepository(session)
            gateway_id = await auth_repo.get_gateway_id_by_api_key(gateway_key)

    logger.info(
        f"WebSocket 连接已接受：{session_id}, 网关: {gateway_id}, Key: {key_id}, 微服务筛选: {microservice_ids}, LLM配置: {llm_config_id}"
    )

    # 动态加载工具：根据选择的微服务加载对应工具
    try:
        async with async_session_factory() as session:
            result = await mcp_tool_registry.load_tools_from_db(
                session, gateway_id=None, force_reload=False
            )
            tool_count = len(result.get("registered", []))
            logger.info(f"已加载工具: {tool_count} 个")
    except Exception as e:
        logger.error(f"加载工具失败: {e}")

    # 获取带 microservice_name 的工具列表（根据选择的微服务筛选）
    tools_with_ms = await mcp_tool_registry.get_tools_with_microservice(microservice_ids)
    allowed_tool_names = [t["name"] for t in tools_with_ms]
    logger.info(f"允许的工具({len(allowed_tool_names)}个): {allowed_tool_names}")

    # 创建 ReAct Agent 会话
    agent_session = react_agent.create_session(
        session_id=session_id,
        gateway_key=gateway_key,
        gateway_id=gateway_id or "",
        key_id=key_id or "",
        llm_key=llm_key,
        llm_config_id=llm_config_id,
        api_type=api_type,
        base_url=base_url,
        model_name=model_name,
        allowed_tool_names=allowed_tool_names,
    )

    # 记录会话开始
    await conversation_logger.log_session_start(
        session_id,
        gateway_key[:10] + "..." if gateway_key else "",
        f"{api_type}:{model_name}" if model_name else "",
    )

    try:
        await websocket.send_json(WSEventFactory.welcome(session_id, tools_with_ms))

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


async def load_tools_from_db(gateway_id: str = None):
    """从数据库加载工具，如果 gateway_id 为 None 则加载所有工具"""
    async with async_session_factory() as session:
        result = await mcp_tool_registry.load_tools_from_db(session, gateway_id)
        return result
