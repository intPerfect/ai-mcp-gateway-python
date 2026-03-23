# -*- coding: utf-8 -*-
"""
API Keys Router - API Key 管理路由
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.utils.result import Result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/apikeys")
async def list_apikeys(db: AsyncSession = Depends(get_db_session)):
    """获取所有 API Key"""
    return Result.success({"apikeys": [], "total": 0})


@router.post("/apikeys")
async def create_apikey(
    name: str,
    gateway_id: str = "gateway_001",
    db: AsyncSession = Depends(get_db_session),
):
    """创建新的 API Key"""
    return Result.success({"id": "", "name": name, "gateway_id": gateway_id})


@router.delete("/apikeys/{key_id}")
async def delete_apikey(key_id: str, db: AsyncSession = Depends(get_db_session)):
    """删除 API Key"""
    return Result.success({"deleted": key_id})
