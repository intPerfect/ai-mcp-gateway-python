# -*- coding: utf-8 -*-
"""
LLM Config Router - LLM配置管理路由
包含：LLM配置CRUD、网关-LLM绑定
"""

import logging
import secrets
from fastapi import APIRouter, Depends

from app.infrastructure.database.models import McpLlmConfig
from app.utils.result import Result
from app.api.deps import UserInfo, DbSession, GatewayRepo, LlmConfigRepo
from app.api.routers.auth import require_permission
from app.api.dependencies import require_gateway_permission
from app.api.schemas.llm_config import (
    LlmConfigCreate,
    LlmConfigUpdate,
    LlmConfigBindRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_config_id() -> str:
    """生成LLM配置ID"""
    return f"llm_{secrets.token_hex(8)}"


# ============================================
# LLM配置管理 API
# ============================================


@router.get("/llm-configs")
async def get_llm_configs(
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:read")),
):
    """获取LLM配置列表"""
    try:
        configs = await llm_config_repo.get_all_llm_configs()

        data = [
            {
                "id": c.id,
                "config_id": c.config_id,
                "config_name": c.config_name,
                "api_type": c.api_type,
                "base_url": c.base_url,
                "model_name": c.model_name,
                "description": c.description,
                "status": c.status,
                "create_time": str(c.create_time) if c.create_time else None,
            }
            for c in configs
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取LLM配置列表失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/llm-configs")
async def create_llm_config(
    form: LlmConfigCreate,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:create")),
):
    """创建LLM配置"""
    try:
        # 生成配置ID
        config_id = _generate_config_id()

        llm_config = McpLlmConfig(
            config_id=config_id,
            config_name=form.config_name,
            api_type=form.api_type,
            base_url=form.base_url,
            model_name=form.model_name,
            api_key=form.api_key,
            description=form.description,
            status=1,
        )

        result = await llm_config_repo.create_llm_config(llm_config)
        logger.info(f"创建LLM配置成功: config_id={config_id}, name={form.config_name}")

        return Result.success(
            {
                "id": result.id,
                "config_id": result.config_id,
                "config_name": result.config_name,
            }
        )
    except Exception as e:
        logger.error(f"创建LLM配置失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/llm-configs/{config_id}")
async def update_llm_config(
    config_id: int,
    form: LlmConfigUpdate,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:update")),
):
    """更新LLM配置"""
    try:
        update_data = {k: v for k, v in form.model_dump().items() if v is not None}
        if not update_data:
            return Result.error("INVALID_PARAM", "无更新数据")

        result = await llm_config_repo.update_llm_config(config_id, **update_data)
        if not result:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        return Result.success({"id": config_id})
    except Exception as e:
        logger.error(f"更新LLM配置失败: {str(e)}")
        return Result.internal_error(str(e))


@router.delete("/llm-configs/{config_id}")
async def delete_llm_config(
    config_id: int,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:delete")),
):
    """删除LLM配置"""
    try:
        success = await llm_config_repo.delete_llm_config(config_id)

        if not success:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        return Result.success({"id": config_id})
    except Exception as e:
        logger.error(f"删除LLM配置失败: {str(e)}")
        return Result.internal_error(str(e))


# ============================================
# 网关-LLM绑定 API
# ============================================


@router.get("/gateways/{gateway_id}/llms")
async def get_gateway_llms(
    gateway_id: str,
    db: DbSession,
    gateway_repo: GatewayRepo,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:read")),
):
    """获取网关绑定的LLM配置列表"""
    try:
        # 验证网关存在
        gateway = await gateway_repo.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "read", current_user, db)

        llm_configs = await llm_config_repo.get_gateway_llm_configs(gateway_id)

        data = [
            {
                "id": c.id,
                "config_id": c.config_id,
                "config_name": c.config_name,
                "api_type": c.api_type,
                "base_url": c.base_url,
                "model_name": c.model_name,
                "description": c.description,
                "status": c.status,
            }
            for c in llm_configs
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取网关LLM列表失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/gateways/{gateway_id}/llms")
async def bind_llm_to_gateway(
    gateway_id: str,
    form: LlmConfigBindRequest,
    db: DbSession,
    gateway_repo: GatewayRepo,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:update")),
):
    """绑定LLM配置到网关"""
    try:
        # 验证网关存在
        gateway = await gateway_repo.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "update", current_user, db)

        # 验证LLM配置存在
        llm_config = await llm_config_repo.get_llm_config_by_config_id(form.llm_config_id)
        if not llm_config:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        # 检查是否已绑定
        is_bound = await llm_config_repo.is_llm_bound_to_gateway(
            gateway_id, form.llm_config_id
        )
        if is_bound:
            return Result.error("ALREADY_BOUND", "该LLM配置已绑定到此网关")

        await llm_config_repo.bind_llm_to_gateway(gateway_id, form.llm_config_id)
        logger.info(
            f"绑定LLM到网关: gateway_id={gateway_id}, llm_config_id={form.llm_config_id}"
        )

        return Result.success(
            {"gateway_id": gateway_id, "llm_config_id": form.llm_config_id}
        )
    except Exception as e:
        logger.error(f"绑定LLM失败: {str(e)}")
        return Result.internal_error(str(e))


@router.delete("/gateways/{gateway_id}/llms/{llm_config_id}")
async def unbind_llm_from_gateway(
    gateway_id: str,
    llm_config_id: str,
    db: DbSession,
    llm_config_repo: LlmConfigRepo,
    current_user: UserInfo = Depends(require_permission("gateway:update")),
):
    """解绑LLM配置"""
    try:
        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "update", current_user, db)

        await llm_config_repo.unbind_llm_from_gateway(gateway_id, llm_config_id)

        logger.info(f"解绑LLM: gateway_id={gateway_id}, llm_config_id={llm_config_id}")
        return Result.success(
            {"gateway_id": gateway_id, "llm_config_id": llm_config_id}
        )
    except Exception as e:
        logger.error(f"解绑LLM失败: {str(e)}")
        return Result.internal_error(str(e))
