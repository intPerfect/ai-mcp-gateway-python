# -*- coding: utf-8 -*-
"""
API Keys Router - API Key 管理路由 (遗留接口，建议使用 gateway-router 中的 gateway-keys 接口)
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.utils.result import Result
from app.api.routers.auth import require_permission, require_auth, UserInfo as CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/apikeys")
async def list_apikeys(
    current_user: CurrentUser = Depends(require_permission("gateway:read")),
    db: AsyncSession = Depends(get_db_session)
):
    """获取所有 API Key（需要gateway:read权限）"""
    return Result.success({"apikeys": [], "total": 0})


@router.post("/apikeys")
async def create_apikey(
    name: str,
    gateway_id: str = "gateway_001",
    current_user: CurrentUser = Depends(require_permission("gateway:create")),
    db: AsyncSession = Depends(get_db_session),
):
    """创建新的 API Key（需要gateway:create权限）"""
    return Result.success({"id": "", "name": name, "gateway_id": gateway_id})


@router.delete("/apikeys/{key_id}")
async def delete_apikey(
    key_id: str,
    current_user: CurrentUser = Depends(require_permission("gateway:delete")),
    db: AsyncSession = Depends(get_db_session)
):
    """删除 API Key（需要gateway:delete权限）"""
    return Result.success({"deleted": key_id})