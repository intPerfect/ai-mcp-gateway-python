# -*- coding: utf-8 -*-
"""
Admin Router - 管理员接口
包含使用统计等管理功能
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.infrastructure.database.models import McpUsageLog, McpGatewayAuth
from app.domain.usage.service import get_usage_service
from app.utils.result import Result
from app.api.deps import CurrentUser, DbSession, PermissionSvc

logger = logging.getLogger(__name__)

router = APIRouter()


class UsageStatsResponse(BaseModel):
    """全局使用统计响应"""

    total_keys: int
    total_calls: int
    active_keys: int
    top_usage: List[dict]


class KeyUsageInfo(BaseModel):
    """单个 Key 使用情况"""

    gateway_id: str
    key_id: str
    key_preview: str
    rate_limit: int
    current_count: int
    remaining: int
    ttl_seconds: int
    window_hours: int


class UsageLogItem(BaseModel):
    """使用日志条目"""

    id: int
    gateway_id: str
    key_id: str
    session_id: Optional[str]
    call_type: str
    call_detail: Optional[str]
    call_time: str
    success: int


@router.get("/usage/stats")
async def get_usage_stats(
    current_user: CurrentUser,
    db: DbSession,
    permission_service: PermissionSvc,
):
    """获取使用统计"""
    try:
        usage_service = await get_usage_service(session=db)

        is_super_admin = "SUPER_ADMIN" in current_user.roles
        accessible_gateway_ids = await permission_service.get_accessible_gateways(
            current_user.id
        )

        if is_super_admin or not accessible_gateway_ids:
            stats = await usage_service.get_all_usage_stats()
        else:
            stats = await usage_service.get_usage_stats_for_gateways(
                accessible_gateway_ids
            )

        return Result.success(
            {
                "total_keys": stats.total_keys,
                "total_calls": stats.total_calls,
                "active_keys": stats.active_keys,
                "top_usage": stats.top_usage,
            }
        )
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}")
        return Result.internal_error(str(e))


@router.get("/usage/keys")
async def get_key_usage_list(
    current_user: CurrentUser,
    db: DbSession,
    permission_service: PermissionSvc,
    gateway_id: Optional[str] = Query(None, description="按网关ID筛选"),
):
    """获取各 Key 使用情况列表"""
    try:
        usage_service = await get_usage_service(session=db)

        is_super_admin = "SUPER_ADMIN" in current_user.roles

        accessible_gateway_ids = await permission_service.get_accessible_gateways(
            current_user.id
        )

        stmt = select(McpGatewayAuth).where(McpGatewayAuth.status == 1)

        if gateway_id:
            stmt = stmt.where(McpGatewayAuth.gateway_id == gateway_id)
            if not is_super_admin and gateway_id not in accessible_gateway_ids:
                return Result.success([])
        elif not is_super_admin and accessible_gateway_ids:
            stmt = stmt.where(McpGatewayAuth.gateway_id.in_(accessible_gateway_ids))

        result = await db.execute(stmt)
        keys = result.scalars().all()

        key_usage_list = []
        for key in keys:
            usage_info = await usage_service.get_usage_info(
                gateway_id=key.gateway_id,
                key_id=key.key_id,
            )
            key_usage_list.append(
                {
                    "gateway_id": key.gateway_id,
                    "key_id": key.key_id,
                    "key_preview": key.key_preview or f"sk-{key.key_id[:8]}...",
                    "rate_limit": usage_info.limit,
                    "current_count": usage_info.current_count,
                    "remaining": usage_info.remaining,
                    "ttl_seconds": usage_info.ttl_seconds,
                    "window_hours": usage_info.window_hours,
                }
            )

        return Result.success(key_usage_list)
    except Exception as e:
        logger.error(f"获取Key使用情况失败: {e}")
        return Result.internal_error(str(e))


@router.get("/usage/logs")
async def get_usage_logs(
    current_user: CurrentUser,
    db: DbSession,
    permission_service: PermissionSvc,
    gateway_id: Optional[str] = Query(None, description="按网关ID筛选"),
    key_id: Optional[str] = Query(None, description="按Key ID筛选"),
    call_type: Optional[str] = Query(None, description="按调用类型筛选: llm/tool"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取使用日志明细（分页）"""
    try:
        is_super_admin = "SUPER_ADMIN" in current_user.roles
        accessible_gateway_ids = await permission_service.get_accessible_gateways(
            current_user.id
        )

        stmt = select(McpUsageLog)

        if gateway_id:
            stmt = stmt.where(McpUsageLog.gateway_id == gateway_id)
            if not is_super_admin and gateway_id not in accessible_gateway_ids:
                return Result.success(
                    {
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "items": [],
                    }
                )
        elif not is_super_admin and accessible_gateway_ids:
            stmt = stmt.where(McpUsageLog.gateway_id.in_(accessible_gateway_ids))

        if key_id:
            stmt = stmt.where(McpUsageLog.key_id == key_id)
        if call_type:
            stmt = stmt.where(McpUsageLog.call_type == call_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.order_by(desc(McpUsageLog.call_time))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        logs = result.scalars().all()

        items = [
            {
                "id": log.id,
                "gateway_id": log.gateway_id,
                "key_id": log.key_id,
                "session_id": log.session_id,
                "call_type": log.call_type,
                "call_detail": log.call_detail,
                "call_time": str(log.call_time) if log.call_time else None,
                "success": log.success,
            }
            for log in logs
        ]

        return Result.success(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items,
            }
        )
    except Exception as e:
        logger.error(f"获取使用日志失败: {e}")
        return Result.internal_error(str(e))


@router.post("/usage/reset")
async def reset_usage(
    current_user: CurrentUser,
    gateway_id: str = Query(..., description="网关ID"),
    key_id: str = Query(..., description="Key ID"),
):
    """重置使用计数（管理员用）"""
    if "SUPER_ADMIN" not in current_user.roles:
        return Result.error("FORBIDDEN", "需要超级管理员权限")

    try:
        usage_service = await get_usage_service()
        success = await usage_service.reset_usage(gateway_id, key_id)

        if success:
            logger.info(f"重置使用计数: {gateway_id}/{key_id}")
            return Result.success({"message": "重置成功"})
        else:
            return Result.internal_error("重置失败")
    except Exception as e:
        logger.error(f"重置使用计数失败: {e}")
        return Result.internal_error(str(e))
