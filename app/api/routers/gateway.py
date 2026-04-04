# -*- coding: utf-8 -*-
"""
Gateway Router - 网关管理路由
包含：网关CRUD、网关-微服务绑定
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import McpGateway, SysBusinessLine
from app.infrastructure.database.repositories import (
    GatewayRepository,
    MicroserviceRepository,
)
from app.utils.result import Result
from app.api.routers.auth import (
    require_auth,
    require_permission,
    UserInfo as CurrentUser,
)
from app.api.dependencies import require_gateway_permission, get_accessible_gateway_ids
from app.api.schemas.gateway import (
    GatewayCreate,
    GatewayUpdate,
    GatewayMicroserviceBind,
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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))
