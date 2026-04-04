# -*- coding: utf-8 -*-
"""
API Dependencies - 统一的权限检查依赖
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rbac.service import PermissionService
from app.domain.rbac import UserInfo
from app.infrastructure.database.models import McpGatewayMicroservice


async def require_gateway_permission(
    gateway_id: str,
    permission_type: str,
    current_user: UserInfo,
    db: AsyncSession,
) -> bool:
    """
    统一的网关权限检查，SUPER_ADMIN 自动放行

    Args:
        gateway_id: 网关ID（字符串标识）
        permission_type: 权限类型 ("read"/"create"/"update"/"delete")
        current_user: 当前用户信息
        db: 数据库会话

    Raises:
        HTTPException: 无权限时抛出 403

    Returns:
        True 表示有权限
    """
    if "SUPER_ADMIN" in current_user.roles:
        return True
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_gateway_permission(
        current_user.id, gateway_id, permission_type
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="无权限操作此网关")
    return True


async def get_accessible_gateway_ids(
    current_user: UserInfo,
    db: AsyncSession,
):
    """
    获取用户可访问的网关ID列表，SUPER_ADMIN 返回 None 表示全部可访问

    Returns:
        Optional[List[str]]: 可访问的网关ID列表，None 表示全部
    """
    if "SUPER_ADMIN" in current_user.roles:
        return None
    permission_service = PermissionService(db)
    return await permission_service.get_accessible_gateways(current_user.id)


async def check_tool_gateway_permission(
    tool, permission_type: str, current_user: UserInfo, db: AsyncSession
):
    """检查用户对工具所属网关的权限，无权限时抛出 HTTPException 403"""
    if "SUPER_ADMIN" in current_user.roles:
        return
    await require_gateway_permission(tool.gateway_id, permission_type, current_user, db)


async def check_microservice_gateway_permission(
    microservice_id: int, permission_type: str, current_user: UserInfo, db: AsyncSession
):
    """检查用户对微服务绑定网关的权限（任一绑定网关有权限即可），无权限时抛出 HTTPException 403"""
    if "SUPER_ADMIN" in current_user.roles:
        return
    # 查询微服务绑定的所有网关
    stmt = select(McpGatewayMicroservice.gateway_id).where(
        McpGatewayMicroservice.microservice_id == microservice_id,
        McpGatewayMicroservice.status == 1,
    )
    result = await db.execute(stmt)
    bound_gateway_ids = [row[0] for row in result.all()]

    if not bound_gateway_ids:
        # 微服务未绑定任何网关，仅依赖角色权限
        return

    # 检查用户对任一绑定网关是否有权限
    permission_service = PermissionService(db)
    for gateway_id in bound_gateway_ids:
        has_permission = await permission_service.check_gateway_permission(
            current_user.id, gateway_id, permission_type
        )
        if has_permission:
            return

    raise HTTPException(status_code=403, detail="无权限操作此微服务关联的网关")
