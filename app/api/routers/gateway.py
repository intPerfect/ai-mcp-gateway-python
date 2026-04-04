# -*- coding: utf-8 -*-
"""
Gateway Router - 网关管理路由
包含：网关配置、网关Key、LLM配置管理、网关-LLM绑定
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import (
    McpGateway,
    McpGatewayAuth,
    McpLlmConfig,
    McpGatewayLlm,
    SysBusinessLine,
)
from app.infrastructure.database import McpGatewayRepository
from app.utils.result import Result
from app.utils.security import generate_api_key, hash_password
from app.api.routers.auth import (
    require_auth,
    require_permission,
    UserInfo as CurrentUser,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Pydantic Schemas
# ============================================


class GatewayCreate(BaseModel):
    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str] = None
    version: str = "1.0.0"
    auth: int = 0


class GatewayUpdate(BaseModel):
    gateway_name: Optional[str] = None
    gateway_desc: Optional[str] = None
    version: Optional[str] = None
    auth: Optional[int] = None
    status: Optional[int] = None


class GatewayKeyCreate(BaseModel):
    gateway_id: str
    rate_limit: int = 600
    expire_days: int = 365
    remark: Optional[str] = None


class LlmConfigCreate(BaseModel):
    config_name: str
    api_type: str  # openai/anthropic
    base_url: str
    model_name: str
    api_key: str  # 明文API Key，后端加密存储
    description: Optional[str] = None


class LlmConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    api_type: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None  # 如果提供新的Key，会加密存储
    description: Optional[str] = None
    status: Optional[int] = None


class GatewayLlmBind(BaseModel):
    llm_config_ids: List[str]


class LlmConfigBindRequest(BaseModel):
    llm_config_id: str


# ============================================
# 网关配置 API
# ============================================


@router.get("/gateways")
async def get_gateways(
    current_user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """获取网关列表（按业务线过滤）"""
    try:
        repository = McpGatewayRepository(db)
        gateways = await repository.get_all_gateways()

        # 获取用户可访问的业务线
        user_bl_ids = (
            [bl.id for bl in current_user.business_lines]
            if current_user.business_lines
            else []
        )

        # 过滤网关（SUPER_ADMIN 可以看到所有网关）
        if "SUPER_ADMIN" in current_user.roles:
            filtered_gateways = gateways
        else:
            filtered_gateways = [
                g
                for g in gateways
                if g.business_line_id is None
                or (user_bl_ids and g.business_line_id in user_bl_ids)
            ]

        data = [
            {
                "id": g.id,
                "gateway_id": g.gateway_id,
                "gateway_name": g.gateway_name,
                "gateway_desc": g.gateway_desc,
                "version": g.version,
                "business_line_id": g.business_line_id,
                "status": g.status,
                "create_time": str(g.create_time) if g.create_time else None,
            }
            for g in filtered_gateways
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取网关列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/gateways")
async def create_gateway(
    form: GatewayCreate,
    current_user: CurrentUser = Depends(require_permission("gateway:create")),
    db: AsyncSession = Depends(get_db_session),
):
    """创建网关"""
    try:
        repository = McpGatewayRepository(db)

        # 检查gateway_id是否已存在
        existing = await repository.get_gateway_by_id(form.gateway_id)
        if existing:
            return Result.error("DUPLICATE_ID", "网关ID已存在")

        gateway = McpGateway(
            gateway_id=form.gateway_id,
            gateway_name=form.gateway_name,
            gateway_desc=form.gateway_desc,
            version=form.version,
            status=1,
        )

        result = await repository.create_gateway(gateway)
        return Result.success(
            {
                "id": result.id,
                "gateway_id": result.gateway_id,
                "gateway_name": result.gateway_name,
            }
        )
    except Exception as e:
        logger.error(f"创建网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.put("/gateways/{gateway_id}")
async def update_gateway(
    gateway_id: int,
    form: GatewayUpdate,
    current_user: CurrentUser = Depends(require_permission("gateway:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """更新网关"""
    try:
        repository = McpGatewayRepository(db)

        update_data = {k: v for k, v in form.model_dump().items() if v is not None}
        if not update_data:
            return Result.error("INVALID_PARAM", "无更新数据")

        result = await repository.update_gateway(gateway_id, **update_data)
        if not result:
            return Result.error("NOT_FOUND", "网关不存在")

        return Result.success({"id": gateway_id})
    except Exception as e:
        logger.error(f"更新网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/gateways/{gateway_id}")
async def delete_gateway(
    gateway_id: int,
    current_user: CurrentUser = Depends(require_permission("gateway:delete")),
    db: AsyncSession = Depends(get_db_session),
):
    """删除网关"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_gateway(gateway_id)

        if not success:
            return Result.error("NOT_FOUND", "网关不存在")

        return Result.success({"id": gateway_id})
    except Exception as e:
        logger.error(f"删除网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# 网关-微服务绑定 API
# ============================================


class GatewayMicroserviceBind(BaseModel):
    microservice_ids: list[int]


@router.get("/gateways/{gateway_id}/microservices")
async def get_gateway_microservices(
    gateway_id: str, db: AsyncSession = Depends(get_db_session)
):
    """获取网关绑定的微服务列表"""
    try:
        repository = McpGatewayRepository(db)
        bindings = await repository.get_gateway_microservices(gateway_id)

        # 获取微服务详情
        microservices = []
        for binding in bindings:
            ms = await repository.get_microservice_by_id(binding.microservice_id)
            if ms:
                # 获取业务线名称
                bl_name = None
                if ms.business_line_id:
                    bl = await db.get(SysBusinessLine, ms.business_line_id)
                    bl_name = bl.line_name if bl else None

                microservices.append(
                    {
                        "id": ms.id,
                        "name": ms.name,
                        "http_base_url": ms.http_base_url,
                        "description": ms.description,
                        "business_line": bl_name or "未分类",
                        "health_status": ms.health_status,
                        "status": ms.status,
                    }
                )

        return Result.success(microservices)
    except Exception as e:
        logger.error(f"获取网关微服务列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.put("/gateways/{gateway_id}/microservices")
async def set_gateway_microservices(
    gateway_id: str,
    form: GatewayMicroserviceBind,
    current_user: CurrentUser = Depends(require_permission("gateway:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """设置网关绑定的微服务（覆盖）"""
    try:
        repository = McpGatewayRepository(db)

        # 验证网关存在
        gateway = await repository.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 验证微服务存在
        for ms_id in form.microservice_ids:
            ms = await repository.get_microservice_by_id(ms_id)
            if not ms:
                return Result.error("NOT_FOUND", f"微服务 {ms_id} 不存在")

        await repository.set_gateway_microservices(gateway_id, form.microservice_ids)

        return Result.success(
            {"gateway_id": gateway_id, "bound_count": len(form.microservice_ids)}
        )
    except Exception as e:
        logger.error(f"设置网关微服务绑定失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# 网关Key API
# ============================================


@router.get("/gateway-keys")
async def get_gateway_keys(
    current_user: CurrentUser = Depends(require_permission("gateway:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取网关Key列表（脱敏）"""
    try:
        repository = McpGatewayRepository(db)
        keys = await repository.get_all_gateway_keys()

        data = [
            {
                "id": k.id,
                "gateway_id": k.gateway_id,
                "key_id": k.key_id,
                "key_preview": k.key_preview or f"sk-{k.key_id[:8]}...",
                "rate_limit": k.rate_limit,
                "expire_time": str(k.expire_time) if k.expire_time else None,
                "remark": k.remark,
                "status": k.status,
                "create_time": str(k.create_time) if k.create_time else None,
            }
            for k in keys
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取网关Key列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/gateway-keys")
async def create_gateway_key(
    form: GatewayKeyCreate,
    current_user: CurrentUser = Depends(require_permission("gateway:create")),
    db: AsyncSession = Depends(get_db_session),
):
    """创建网关Key（返回完整Key，仅此一次）"""
    try:
        repository = McpGatewayRepository(db)

        # 生成 API Key
        key_id, full_api_key = generate_api_key()
        api_key_hash = hash_password(full_api_key)
        key_preview = f"sk-{key_id[:8]}...{full_api_key[-4:]}"

        expire_time = datetime.now() + timedelta(days=form.expire_days)

        auth = McpGatewayAuth(
            gateway_id=form.gateway_id,
            key_id=key_id,
            api_key_hash=api_key_hash,
            key_preview=key_preview,
            rate_limit=form.rate_limit,
            expire_time=expire_time,
            remark=form.remark,
            status=1,
        )

        await repository.create_gateway_key(auth)

        logger.info(f"创建网关Key成功: gateway_id={form.gateway_id}, key_id={key_id}")

        return Result.success(
            {
                "id": auth.id,
                "gateway_id": form.gateway_id,
                "api_key": full_api_key,  # 完整Key仅在创建时返回
                "key_preview": key_preview,
                "expire_time": expire_time.isoformat(),
                "message": "请立即保存API Key，关闭后将无法再次查看完整Key",
            }
        )
    except Exception as e:
        logger.error(f"创建网关Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/gateway-keys/{key_id}")
async def delete_gateway_key(
    key_id: int,
    current_user: CurrentUser = Depends(require_permission("gateway:delete")),
    db: AsyncSession = Depends(get_db_session),
):
    """删除网关Key"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_gateway_key(key_id)

        if not success:
            return Result.error("NOT_FOUND", "Key不存在")

        return Result.success({"id": key_id})
    except Exception as e:
        logger.error(f"删除网关Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# LLM配置管理 API (v10.0)
# ============================================


def _generate_config_id() -> str:
    """生成LLM配置ID"""
    import secrets

    return f"llm_{secrets.token_hex(8)}"


@router.get("/llm-configs")
async def get_llm_configs(
    current_user: CurrentUser = Depends(require_permission("gateway:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取LLM配置列表"""
    try:
        repository = McpGatewayRepository(db)
        configs = await repository.get_all_llm_configs()

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
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/llm-configs")
async def create_llm_config(
    form: LlmConfigCreate,
    current_user: CurrentUser = Depends(require_permission("gateway:create")),
    db: AsyncSession = Depends(get_db_session),
):
    """创建LLM配置"""
    try:
        repository = McpGatewayRepository(db)

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

        result = await repository.create_llm_config(llm_config)
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
        return Result.error("SYSTEM_ERROR", str(e))


@router.put("/llm-configs/{config_id}")
async def update_llm_config(
    config_id: int,
    form: LlmConfigUpdate,
    current_user: CurrentUser = Depends(require_permission("gateway:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """更新LLM配置"""
    try:
        repository = McpGatewayRepository(db)

        update_data = {k: v for k, v in form.model_dump().items() if v is not None}
        if not update_data:
            return Result.error("INVALID_PARAM", "无更新数据")

        result = await repository.update_llm_config(config_id, **update_data)
        if not result:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        return Result.success({"id": config_id})
    except Exception as e:
        logger.error(f"更新LLM配置失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/llm-configs/{config_id}")
async def delete_llm_config(
    config_id: int,
    current_user: CurrentUser = Depends(require_permission("gateway:delete")),
    db: AsyncSession = Depends(get_db_session),
):
    """删除LLM配置"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_llm_config(config_id)

        if not success:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        return Result.success({"id": config_id})
    except Exception as e:
        logger.error(f"删除LLM配置失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# 网关-LLM绑定 API (v10.0)
# ============================================


@router.get("/gateways/{gateway_id}/llms")
async def get_gateway_llms(
    gateway_id: str,
    current_user: CurrentUser = Depends(require_permission("gateway:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取网关绑定的LLM配置列表"""
    try:
        repository = McpGatewayRepository(db)

        # 验证网关存在
        gateway = await repository.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        llm_configs = await repository.get_gateway_llm_configs(gateway_id)

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
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/gateways/{gateway_id}/llms")
async def bind_llm_to_gateway(
    gateway_id: str,
    form: LlmConfigBindRequest,
    current_user: CurrentUser = Depends(require_permission("gateway:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """绑定LLM配置到网关"""
    try:
        repository = McpGatewayRepository(db)

        # 验证网关存在
        gateway = await repository.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 验证LLM配置存在
        llm_config = await repository.get_llm_config_by_config_id(form.llm_config_id)
        if not llm_config:
            return Result.error("NOT_FOUND", "LLM配置不存在")

        # 检查是否已绑定
        is_bound = await repository.is_llm_bound_to_gateway(
            gateway_id, form.llm_config_id
        )
        if is_bound:
            return Result.error("ALREADY_BOUND", "该LLM配置已绑定到此网关")

        await repository.bind_llm_to_gateway(gateway_id, form.llm_config_id)
        logger.info(
            f"绑定LLM到网关: gateway_id={gateway_id}, llm_config_id={form.llm_config_id}"
        )

        return Result.success(
            {"gateway_id": gateway_id, "llm_config_id": form.llm_config_id}
        )
    except Exception as e:
        logger.error(f"绑定LLM失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/gateways/{gateway_id}/llms/{llm_config_id}")
async def unbind_llm_from_gateway(
    gateway_id: str,
    llm_config_id: str,
    current_user: CurrentUser = Depends(require_permission("gateway:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """解绑LLM配置"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.unbind_llm_from_gateway(gateway_id, llm_config_id)

        logger.info(f"解绑LLM: gateway_id={gateway_id}, llm_config_id={llm_config_id}")
        return Result.success(
            {"gateway_id": gateway_id, "llm_config_id": llm_config_id}
        )
    except Exception as e:
        logger.error(f"解绑LLM失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))
