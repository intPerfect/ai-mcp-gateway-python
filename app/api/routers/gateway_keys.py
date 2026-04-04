# -*- coding: utf-8 -*-
"""
Gateway Keys Router - 网关Key管理路由
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import McpGatewayAuth
from app.infrastructure.database.repositories import AuthRepository
from app.utils.result import Result
from app.utils.security import generate_api_key, hash_password
from app.api.routers.auth import (
    require_permission,
    UserInfo as CurrentUser,
)
from app.api.dependencies import require_gateway_permission, get_accessible_gateway_ids
from app.api.schemas.gateway import GatewayKeyCreate

logger = logging.getLogger(__name__)

router = APIRouter()


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))


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
        return Result.internal_error(str(e))
