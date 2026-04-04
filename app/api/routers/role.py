# -*- coding: utf-8 -*-
"""
Role Router - 角色管理API路由
"""

import logging
from typing import List
from fastapi import APIRouter, Depends

from app.infrastructure.database.models import SysRole
from app.infrastructure.cache.redis_client import get_redis, PermissionCache
from app.domain.rbac import RoleInfo, RoleCreate, RoleUpdate, DataPermissionSet
from app.utils.result import Result
from app.api.deps import (
    UserInfo, is_super_admin, get_user_managed_business_line_ids,
    RoleRepo, PermissionRepo, BusinessLineRepo,
    GatewayPermissionRepo, GatewayRepo,
)
from app.api.routers.auth import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roles", tags=["角色管理"])


def role_to_info(
    role: SysRole,
    permissions: List[str] = None,
    permission_ids: List[int] = None,
    data_permissions: DataPermissionSet = None,
    business_line_name: str = None,
) -> RoleInfo:
    """转换ORM模型到Info模型"""
    return RoleInfo(
        id=role.id,
        role_code=role.role_code,
        role_name=role.role_name,
        description=role.description,
        business_line_id=role.business_line_id,
        business_line_name=business_line_name,
        is_system=role.is_system,
        status=role.status,
        permissions=permissions or [],
        permission_ids=permission_ids or [],
        data_permissions=data_permissions,
        create_time=role.create_time,
    )


@router.get("", response_model=Result[List[RoleInfo]])
async def list_roles(
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:read")),
):
    """获取角色列表

    - 超级管理员：可以看到所有角色
    - 业务线管理员：只能看到全局角色和自己业务线的角色
    """
    roles = await role_repo.get_all_roles()

    # 获取业务线映射
    business_lines = await business_line_repo.get_all_business_lines()
    bl_map = {bl.id: bl.line_name for bl in business_lines}

    # 权限过滤
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        roles = [
            r
            for r in roles
            if r.business_line_id is None or r.business_line_id in managed_bl_ids
        ]

    result = []
    for role in roles:
        perms = await permission_repo.get_role_permissions(role.id)
        perm_codes = [p.permission_code for p in perms]
        perm_ids = [p.id for p in perms]
        bl_name = bl_map.get(role.business_line_id) if role.business_line_id else None
        result.append(role_to_info(role, perm_codes, perm_ids, None, bl_name))

    return Result.success(data=result)


@router.get("/assignable", response_model=Result[List[RoleInfo]])
async def get_assignable_roles(
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    current_user: UserInfo = Depends(require_permission("user:create")),
):
    """获取当前用户可分配的角色列表

    - 超级管理员：可以分配所有非超级管理员角色
    - 业务线管理员：只能分配全局角色和自己业务线的角色（排除超级管理员）
    """
    # 获取业务线映射
    business_lines = await business_line_repo.get_all_business_lines()
    bl_map = {bl.id: bl.line_name for bl in business_lines}

    # 先排除超级管理员角色
    all_roles = await role_repo.get_all_roles()
    non_super_roles = [r for r in all_roles if r.role_code != "SUPER_ADMIN"]

    if is_super_admin(current_user):
        roles = non_super_roles
    else:
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if not managed_bl_ids:
            return Result.success(data=[])

        roles = [
            r
            for r in non_super_roles
            if r.business_line_id is None or r.business_line_id in managed_bl_ids
        ]

    result = []
    for role in roles:
        bl_name = bl_map.get(role.business_line_id) if role.business_line_id else None
        result.append(role_to_info(role, [], [], None, bl_name))

    return Result.success(data=result)


@router.get("/{role_id}", response_model=Result[RoleInfo])
async def get_role(
    role_id: int,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:read")),
):
    """获取角色详情"""
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    # 权限校验：业务线管理员只能查看自己业务线的角色
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权查看该角色")

    perms = await permission_repo.get_role_permissions(role.id)
    perm_codes = [p.permission_code for p in perms]
    perm_ids = [p.id for p in perms]

    # 获取业务线名称
    bl_name = None
    if role.business_line_id:
        bl = await business_line_repo.get_business_line_by_id(role.business_line_id)
        bl_name = bl.line_name if bl else None

    return Result.success(data=role_to_info(role, perm_codes, perm_ids, None, bl_name))


@router.post("", response_model=Result[RoleInfo])
async def create_role(
    request: RoleCreate,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:create")),
):
    """创建角色

    - 超级管理员：可以创建全局角色（business_line_id=None）或任意业务线角色
    - 业务线管理员：只能创建自己业务线的角色，business_line_id会被强制设置为用户管理的业务线
    """
    # 检查角色编码是否已存在
    existing = await role_repo.get_role_by_code(request.role_code)
    if existing:
        return Result.fail(code="2001", message="角色编码已存在")

    # 确定业务线ID
    business_line_id = request.business_line_id

    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)

        if not managed_bl_ids:
            return Result.fail(
                code="403", message="您不是任何业务线的管理员，无法创建角色"
            )

        if business_line_id is not None:
            if business_line_id not in managed_bl_ids:
                return Result.fail(
                    code="403", message="您只能在自己管理的业务线下创建角色"
                )
        else:
            business_line_id = managed_bl_ids[0]

    role = SysRole(
        role_code=request.role_code,
        role_name=request.role_name,
        description=request.description,
        business_line_id=business_line_id,
        is_system=0,
        status=1,
    )

    role = await role_repo.create_role(role)

    # 分配权限
    if request.permission_ids:
        await permission_repo.set_role_permissions(role.id, request.permission_ids)

    # 获取业务线名称
    bl_name = None
    if role.business_line_id:
        bl = await business_line_repo.get_business_line_by_id(role.business_line_id)
        bl_name = bl.line_name if bl else None

    logger.info(
        f"Role {role.role_code} created by {current_user.username} with business_line_id={business_line_id}"
    )

    return Result.success(
        data=role_to_info(role, [], [], None, bl_name), message="创建成功"
    )


@router.put("/{role_id}", response_model=Result[RoleInfo])
async def update_role(
    role_id: int,
    request: RoleUpdate,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:update")),
):
    """更新角色"""
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    if role.is_system == 1:
        return Result.fail(code="2003", message="系统内置角色不可修改")

    # 权限校验：业务线管理员只能修改自己业务线的角色
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权修改该角色")

    update_data = {}
    if request.role_name is not None:
        update_data["role_name"] = request.role_name
    if request.description is not None:
        update_data["description"] = request.description
    if request.status is not None:
        update_data["status"] = request.status

    if update_data:
        role = await role_repo.update_role(role_id, **update_data)

    # 更新权限
    if request.permission_ids is not None:
        await permission_repo.set_role_permissions(role_id, request.permission_ids)

    # 获取业务线名称
    bl_name = None
    if role.business_line_id:
        bl = await business_line_repo.get_business_line_by_id(role.business_line_id)
        bl_name = bl.line_name if bl else None

    logger.info(f"Role {role.role_code} updated by {current_user.username}")

    return Result.success(
        data=role_to_info(role, [], [], None, bl_name), message="更新成功"
    )


@router.delete("/{role_id}", response_model=Result)
async def delete_role(
    role_id: int,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    current_user: UserInfo = Depends(require_permission("role:delete")),
):
    """删除角色"""
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    if role.is_system == 1:
        return Result.fail(code="2003", message="系统内置角色不可删除")

    # 权限校验：业务线管理员只能删除自己业务线的角色
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权删除该角色")

    await role_repo.delete_role(role_id)
    logger.info(f"Role {role.role_code} deleted by {current_user.username}")

    return Result.success(message="删除成功")


@router.get("/{role_id}/permissions", response_model=Result[List[str]])
async def get_role_permissions(
    role_id: int,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:read")),
):
    """获取角色权限列表"""
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    # 权限校验
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权查看该角色")

    perms = await permission_repo.get_role_permissions(role.id)
    perm_codes = [p.permission_code for p in perms]

    return Result.success(data=perm_codes)


@router.put("/{role_id}/permissions", response_model=Result)
async def set_role_permissions(
    role_id: int,
    permission_ids: List[int],
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    permission_repo: PermissionRepo,
    current_user: UserInfo = Depends(require_permission("role:update")),
):
    """设置角色权限"""
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    # 权限校验
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权修改该角色")

    await permission_repo.set_role_permissions(role_id, permission_ids)
    logger.info(f"Permissions set for role {role.role_code} by {current_user.username}")

    # 失效缓存
    try:
        redis = await get_redis()
        cache = PermissionCache(redis)
        await cache.invalidate_role_related(role_id)
    except Exception as e:
        logger.warning(f"失效缓存失败: {e}")

    return Result.success(message="权限设置成功")


@router.get("/{role_id}/gateway-permissions", response_model=Result[List])
async def get_role_gateway_permissions(
    role_id: int,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    gateway_permission_repo: GatewayPermissionRepo,
    gateway_repo: GatewayRepo,
    current_user: UserInfo = Depends(require_permission("role:read")),
):
    """获取角色的网关权限

    - 超级管理员：可以看到所有网关的权限
    - 业务线管理员：只能看到自己业务线范围内的网关权限
    """
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    # 权限校验
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权查看该角色")

    # 获取所有网关和业务线
    gateways = await gateway_repo.get_all_gateways()
    business_lines = await business_line_repo.get_all_business_lines()
    bl_map = {bl.id: bl.line_name for bl in business_lines}

    # 业务线管理员只能看到自己业务线范围内的网关
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        gateways = [
            gw
            for gw in gateways
            if gw.business_line_id is None or gw.business_line_id in managed_bl_ids
        ]

    # 获取角色的网关权限
    permissions = await gateway_permission_repo.get_gateway_permissions_by_role(role_id)

    # 构建权限映射
    perm_map = {p.gateway_id: p for p in permissions}

    result = []
    for gw in gateways:
        perm = perm_map.get(gw.gateway_id)
        bl_name = bl_map.get(gw.business_line_id) if gw.business_line_id else None
        result.append(
            {
                "gateway_id": gw.gateway_id,
                "gateway_name": gw.gateway_name,
                "business_line_id": gw.business_line_id,
                "business_line_name": bl_name,
                "can_create": bool(perm.can_create) if perm else False,
                "can_read": bool(perm.can_read) if perm else False,
                "can_update": bool(perm.can_update) if perm else False,
                "can_delete": bool(perm.can_delete) if perm else False,
                "can_chat": bool(perm.can_chat) if perm else False,
            }
        )

    return Result.success(data=result)


@router.put("/{role_id}/gateway-permissions", response_model=Result)
async def set_role_gateway_permissions(
    role_id: int,
    request: List[dict],
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    gateway_permission_repo: GatewayPermissionRepo,
    gateway_repo: GatewayRepo,
    current_user: UserInfo = Depends(require_permission("role:update")),
):
    """设置角色的网关权限
    
    - 超级管理员：可以设置所有网关的权限
    - 业务线管理员：只能设置自己业务线范围内的网关权限
    """
    role = await role_repo.get_role_by_id(role_id)

    if not role:
        return Result.not_found("角色不存在")

    # 权限校验
    managed_bl_ids = None
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return Result.fail(code="403", message="无权修改该角色")

    # 获取所有网关
    gateways = await gateway_repo.get_all_gateways()
    gateway_bl_map = {gw.gateway_id: gw.business_line_id for gw in gateways}

    # 转换请求格式，业务线管理员只能设置自己业务线范围内的网关
    permissions = []
    for item in request:
        gateway_id = item["gateway_id"]
        
        # 业务线管理员检查网关是否在自己业务线范围内
        if managed_bl_ids is not None:
            gw_bl_id = gateway_bl_map.get(gateway_id)
            if gw_bl_id is not None and gw_bl_id not in managed_bl_ids:
                continue  # 跳过不在范围内的网关
        
        permissions.append(
            {
                "gateway_id": gateway_id,
                "can_create": item.get("can_create", False),
                "can_read": item.get("can_read", False),
                "can_update": item.get("can_update", False),
                "can_delete": item.get("can_delete", False),
                "can_chat": item.get("can_chat", False),
            }
        )

    if managed_bl_ids is not None:
        scoped_gateway_ids = [
            gw.gateway_id
            for gw in gateways
            if gw.business_line_id is None or gw.business_line_id in managed_bl_ids
        ]
        await gateway_permission_repo.set_role_gateway_permissions_scoped(
            role_id, permissions, scoped_gateway_ids
        )
    else:
        await gateway_permission_repo.set_role_gateway_permissions(role_id, permissions)

    logger.info(
        f"Gateway permissions set for role {role.role_code} by {current_user.username}"
    )

    # 失效缓存
    try:
        redis = await get_redis()
        cache = PermissionCache(redis)
        await cache.invalidate_role_related(role_id)
    except Exception as e:
        logger.warning(f"失效缓存失败: {e}")

    return Result.success(message="网关权限设置成功")


@router.get("/{role_id}/bl-admin", response_model=Result[List[int]])
async def get_role_bl_admin(
    role_id: int,
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    current_user: UserInfo = Depends(require_permission("role:read")),
):
    """获取角色的业务线管理员权限"""
    role = await role_repo.get_role_by_id(role_id)
    if not role:
        return Result.not_found("角色不存在")

    bl_admin_ids = await business_line_repo.get_role_bl_admin_ids(role_id)
    return Result.success(data=bl_admin_ids)


@router.put("/{role_id}/bl-admin", response_model=Result)
async def set_role_bl_admin(
    role_id: int,
    bl_ids: List[int],
    role_repo: RoleRepo,
    business_line_repo: BusinessLineRepo,
    current_user: UserInfo = Depends(require_permission("role:update")),
):
    """设置角色的业务线管理员权限"""
    role = await role_repo.get_role_by_id(role_id)
    if not role:
        return Result.not_found("角色不存在")

    # 权限校验
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(business_line_repo, current_user.id)
        if role.business_line_id is not None and role.business_line_id not in managed_bl_ids:
            return Result.fail(code="403", message="无权修改该角色")
        # 业务线管理员只能设置自己管理的业务线
        bl_ids = [bl_id for bl_id in bl_ids if bl_id in managed_bl_ids]

    await business_line_repo.set_role_bl_admin_ids(role_id, bl_ids)
    logger.info(f"BL admin set for role {role.role_code} by {current_user.username}: {bl_ids}")

    # 失效缓存
    try:
        redis = await get_redis()
        cache = PermissionCache(redis)
        await cache.invalidate_role_related(role_id)
    except Exception as e:
        logger.warning(f"失效缓存失败: {e}")

    return Result.success(message="业务线管理员权限设置成功")
