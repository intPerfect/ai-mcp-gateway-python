# -*- coding: utf-8 -*-
"""
Gateway Router - 网关管理路由
包含：网关配置、网关Key、LLM配置管理、网关-LLM绑定
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import (
    McpGateway,
    McpGatewayAuth,
    McpLlmConfig,
    SysBusinessLine,
)
from app.infrastructure.database.repositories import (
    GatewayRepository,
    AuthRepository,
    LlmConfigRepository,
    MicroserviceRepository,
)
from app.utils.result import Result
from app.utils.security import generate_api_key, hash_password
from app.api.routers.auth import (
    require_auth,
    require_permission,
    UserInfo as CurrentUser,
)
from app.api.dependencies import require_gateway_permission, get_accessible_gateway_ids
from app.api.schemas.gateway import (
    GatewayCreate,
    GatewayUpdate,
    GatewayKeyCreate,
    GatewayMicroserviceBind,
)
from app.api.schemas.llm_config import (
    LlmConfigCreate,
    LlmConfigUpdate,
    LlmConfigBindRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# 网关配置 API
# ============================================


@router.get("/gateways")
async def get_gateways(
    current_user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """获取网关列表（基于sys_gateway_permission权限过滤）"""
    try:
        repository = GatewayRepository(db)
        gateways = await repository.get_all_gateways()

        # 基于权限过滤网关列表
        accessible_ids = await get_accessible_gateway_ids(current_user, db)
        if accessible_ids is None:
            filtered_gateways = gateways  # SUPER_ADMIN 可看全部
        elif accessible_ids:
            filtered_gateways = [
                g for g in gateways if g.gateway_id in accessible_ids
            ]
        else:
            filtered_gateways = []

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
        repository = GatewayRepository(db)

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
        repository = GatewayRepository(db)

        # 先获取网关信息
        gateway = await repository.get_gateway_by_numeric_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 检查用户对该网关的数据权限
        await require_gateway_permission(gateway.gateway_id, "update", current_user, db)

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
        repository = GatewayRepository(db)

        # 先获取网关信息
        gateway = await repository.get_gateway_by_numeric_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 检查用户对该网关的数据权限
        await require_gateway_permission(gateway.gateway_id, "delete", current_user, db)

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


@router.get("/gateways/{gateway_id}/microservices")
async def get_gateway_microservices(
    gateway_id: str,
    current_user: CurrentUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """获取网关绑定的微服务列表"""
    try:
        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "read", current_user, db)

        repository = GatewayRepository(db)
        ms_repo = MicroserviceRepository(db)
        bindings = await repository.get_gateway_microservices(gateway_id)

        # 获取微服务详情
        microservices = []
        for binding in bindings:
            ms = await ms_repo.get_microservice_by_id(binding.microservice_id)
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
        repository = GatewayRepository(db)
        ms_repo = MicroserviceRepository(db)

        # 验证网关存在
        gateway = await repository.get_gateway_by_id(gateway_id)
        if not gateway:
            return Result.error("NOT_FOUND", "网关不存在")

        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "update", current_user, db)

        # 验证微服务存在
        for ms_id in form.microservice_ids:
            ms = await ms_repo.get_microservice_by_id(ms_id)
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
    """获取网关Key列表（脱敏，按权限过滤）"""
    try:
        repository = AuthRepository(db)
        keys = await repository.get_all_gateway_keys()

        # 按权限过滤
        accessible_ids = await get_accessible_gateway_ids(current_user, db)
        if accessible_ids is not None:
            keys = [k for k in keys if k.gateway_id in accessible_ids]

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
        # 检查网关级别权限
        await require_gateway_permission(form.gateway_id, "create", current_user, db)

        repository = AuthRepository(db)

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
        repository = AuthRepository(db)

        # 先获取Key信息以检查权限
        key = await repository.get_gateway_key_by_id(key_id)
        if not key:
            return Result.error("NOT_FOUND", "Key不存在")

        # 检查网关级别权限
        await require_gateway_permission(key.gateway_id, "delete", current_user, db)

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
        repository = LlmConfigRepository(db)
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
        repository = LlmConfigRepository(db)

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

        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "read", current_user, db)

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

        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "update", current_user, db)

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
        # 检查网关级别权限
        await require_gateway_permission(gateway_id, "update", current_user, db)

        repository = McpGatewayRepository(db)
        await repository.unbind_llm_from_gateway(gateway_id, llm_config_id)

        logger.info(f"解绑LLM: gateway_id={gateway_id}, llm_config_id={llm_config_id}")
        return Result.success(
            {"gateway_id": gateway_id, "llm_config_id": llm_config_id}
        )
    except Exception as e:
        logger.error(f"解绑LLM失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))
