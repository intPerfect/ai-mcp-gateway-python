# -*- coding: utf-8 -*-
"""
User Router - 用户管理API路由
"""

import logging
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repository import RbacRepository
from app.infrastructure.database.models import SysUser
from app.domain.rbac import UserInfo, UserCreate, UserUpdate, BusinessLineInfo
from app.utils.security import hash_password
from app.utils.result import Result
from app.api.routers.auth import (
    require_permission,
    UserInfo as CurrentUser,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def user_to_info(
    user: SysUser,
    roles: List[str] = None,
    permissions: List[str] = None,
    role_ids: List[int] = None,
    business_lines: List = None,
    managed_business_lines: List = None,
) -> UserInfo:
    """转换ORM模型到Info模型"""
    return UserInfo(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        email=user.email,
        phone=user.phone,
        avatar=user.avatar,
        status=user.status,
        roles=roles or [],
        role_ids=role_ids or [],
        permissions=permissions or [],
        business_lines=business_lines or [],
        managed_business_lines=managed_business_lines or [],
        create_time=user.create_time,
    )


def is_super_admin(current_user: CurrentUser) -> bool:
    """检查是否是超级管理员"""
    return "SUPER_ADMIN" in current_user.roles


async def get_user_managed_business_line_ids(
    repo: RbacRepository, user_id: int
) -> List[int]:
    """获取用户管理的业务线ID列表"""
    managed = await repo.get_user_managed_business_lines(user_id)
    return [ubl.business_line_id for ubl in managed]


async def validate_role_assignment(
    repo: RbacRepository, current_user: CurrentUser, role_ids: List[int]
) -> tuple[bool, str]:
    """验证用户是否有权限分配指定角色

    Returns:
        (is_valid, error_message)
    """
    if not role_ids:
        return True, None

    if is_super_admin(current_user):
        # 超级管理员可以分配任意角色
        return True, None

    # 非超级管理员不能分配超级管理员角色
    for role_id in role_ids:
        role = await repo.get_role_by_id(role_id)
        if role and role.role_code == "SUPER_ADMIN":
            return False, "无权分配超级管理员角色"

    # 获取用户管理的业务线
    managed_bl_ids = await get_user_managed_business_line_ids(repo, current_user.id)

    if not managed_bl_ids:
        return False, "您不是任何业务线的管理员，无法分配角色"

    # 检查每个角色
    for role_id in role_ids:
        role = await repo.get_role_by_id(role_id)
        if not role:
            return False, f"角色ID {role_id} 不存在"

        # 只能分配全局角色或自己业务线的角色
        if (
            role.business_line_id is not None
            and role.business_line_id not in managed_bl_ids
        ):
            return False, f"无权分配角色 '{role.role_name}'，该角色不属于您管理的业务线"

    return True, None


@router.get("", response_model=Result[List[UserInfo]])
async def list_users(
    current_user: CurrentUser = Depends(require_permission("user:read")),
    session: AsyncSession = Depends(get_db_session),
):
    """获取用户列表

    - 超级管理员：返回所有用户
    - 业务线管理员：只返回属于其业务线的用户
    """
    repo = RbacRepository(session)
    users = await repo.get_all_users()

    # 业务线管理员只能看到其业务线下的用户
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(repo, current_user.id)
        if managed_bl_ids:
            # 筛选属于管理业务线的用户
            filtered_users = []
            for user in users:
                # 获取用户的角色
                user_roles = await repo.get_user_roles(user.id)
                user_bl_ids = set()
                for role in user_roles:
                    if role.business_line_id:
                        user_bl_ids.add(role.business_line_id)

                # 检查是否有交集
                if user_bl_ids & set(managed_bl_ids):
                    filtered_users.append(user)
            users = filtered_users
        else:
            # 没有管理任何业务线，返回空列表
            return Result.success(data=[])

    result = []
    for user in users:
        roles = []
        role_ids = []
        permissions = []
        user_bls = []
        user_managed_bls = []

        user_roles = await repo.get_user_roles(user.id)
        roles = [r.role_code for r in user_roles]
        role_ids = [r.id for r in user_roles]

        user_perms = await repo.get_user_permissions(user.id)
        permissions = [p.permission_code for p in user_perms]

        # 获取用户所属业务线
        user_business_lines = await repo.get_user_business_lines(user.id)
        for ubl in user_business_lines:
            bl = await repo.get_business_line_by_id(ubl.business_line_id)
            if bl:
                user_bls.append(
                    BusinessLineInfo(
                        id=bl.id,
                        line_code=bl.line_code,
                        line_name=bl.line_name,
                        description=bl.description,
                        status=bl.status,
                        is_admin=bool(ubl.is_admin),
                        create_time=bl.create_time,
                    )
                )

        # 获取用户管理的业务线
        user_managed_business_lines = await repo.get_user_managed_business_lines(
            user.id
        )
        for ubl in user_managed_business_lines:
            bl = await repo.get_business_line_by_id(ubl.business_line_id)
            if bl:
                user_managed_bls.append(
                    BusinessLineInfo(
                        id=bl.id,
                        line_code=bl.line_code,
                        line_name=bl.line_name,
                        description=bl.description,
                        status=bl.status,
                        is_admin=True,
                        create_time=bl.create_time,
                    )
                )

        result.append(
            user_to_info(user, roles, permissions, role_ids, user_bls, user_managed_bls)
        )

    return Result.success(data=result)


@router.get("/{user_id}", response_model=Result[UserInfo])
async def get_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_permission("user:read")),
    session: AsyncSession = Depends(get_db_session),
):
    """获取用户详情"""
    repo = RbacRepository(session)
    user = await repo.get_user_by_id(user_id)

    if not user:
        return Result.not_found("用户不存在")

    user_roles = await repo.get_user_roles(user.id)
    roles = [r.role_code for r in user_roles]
    role_ids = [r.id for r in user_roles]

    user_perms = await repo.get_user_permissions(user.id)
    permissions = [p.permission_code for p in user_perms]

    user_bls = []
    user_managed_bls = []

    # 获取用户所属业务线
    user_business_lines = await repo.get_user_business_lines(user.id)
    for ubl in user_business_lines:
        bl = await repo.get_business_line_by_id(ubl.business_line_id)
        if bl:
            user_bls.append(
                BusinessLineInfo(
                    id=bl.id,
                    line_code=bl.line_code,
                    line_name=bl.line_name,
                    description=bl.description,
                    status=bl.status,
                    is_admin=bool(ubl.is_admin),
                    create_time=bl.create_time,
                )
            )

    # 获取用户管理的业务线
    user_managed_business_lines = await repo.get_user_managed_business_lines(user.id)
    for ubl in user_managed_business_lines:
        bl = await repo.get_business_line_by_id(ubl.business_line_id)
        if bl:
            user_managed_bls.append(
                BusinessLineInfo(
                    id=bl.id,
                    line_code=bl.line_code,
                    line_name=bl.line_name,
                    description=bl.description,
                    status=bl.status,
                    is_admin=True,
                    create_time=bl.create_time,
                )
            )

    return Result.success(
        data=user_to_info(
            user, roles, permissions, role_ids, user_bls, user_managed_bls
        )
    )


@router.post("", response_model=Result[UserInfo])
async def create_user(
    request: UserCreate,
    current_user: CurrentUser = Depends(require_permission("user:create")),
    session: AsyncSession = Depends(get_db_session),
):
    """创建用户

    - 超级管理员：可以分配任意角色
    - 业务线管理员：只能分配全局角色或自己业务线的角色
    - 用户必须属于至少一个业务线，默认分配到"其他"业务线
    """
    repo = RbacRepository(session)

    # 检查用户名是否已存在
    existing = await repo.get_user_by_username(request.username)
    if existing:
        return Result.fail(code="2001", message="用户名已存在")

    # 验证角色分配权限
    if request.role_ids:
        is_valid, error_msg = await validate_role_assignment(
            repo, current_user, request.role_ids
        )
        if not is_valid:
            return Result.fail(code="403", message=error_msg)

    # 创建用户
    user = SysUser(
        username=request.username,
        password_hash=hash_password(request.password),
        real_name=request.real_name,
        email=request.email,
        phone=request.phone,
        status=1,
    )

    user = await repo.create_user(user)

    # 分配角色
    if request.role_ids:
        await repo.set_user_roles(user.id, request.role_ids)

    # 分配业务线：至少分配一个业务线，默认使用"其他"业务线
    bl_ids = request.business_line_ids if request.business_line_ids else []
    if not bl_ids:
        # 默认分配到"其他"业务线
        other_bl = await repo.get_business_line_by_code("OTHER")
        if other_bl:
            bl_ids = [other_bl.id]

    for bl_id in bl_ids:
        await repo.add_user_to_business_line(user.id, bl_id)

    logger.info(f"User {user.username} created by {current_user.username}")

    return Result.success(data=user_to_info(user), message="创建成功")


@router.put("/{user_id}", response_model=Result[UserInfo])
async def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: CurrentUser = Depends(require_permission("user:update")),
    session: AsyncSession = Depends(get_db_session),
):
    """更新用户

    - 超级管理员：可以更新任意用户
    - 业务线管理员：只能更新自己业务线下的用户
    """
    repo = RbacRepository(session)
    user = await repo.get_user_by_id(user_id)

    if not user:
        return Result.not_found("用户不存在")

    # 业务线权限检查
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(repo, current_user.id)
        if managed_bl_ids:
            # 检查目标用户是否属于当前用户管理的业务线
            user_roles = await repo.get_user_roles(user_id)
            user_bl_ids = set()
            for role in user_roles:
                if role.business_line_id:
                    user_bl_ids.add(role.business_line_id)
            if not (user_bl_ids & set(managed_bl_ids)):
                return Result.fail(
                    code="403", message="无权更新该用户，该用户不属于您管理的业务线"
                )

    # 验证角色分配权限
    if request.role_ids is not None:
        is_valid, error_msg = await validate_role_assignment(
            repo, current_user, request.role_ids
        )
        if not is_valid:
            return Result.fail(code="403", message=error_msg)

    # 构建更新数据
    update_data = {}
    if request.real_name is not None:
        update_data["real_name"] = request.real_name
    if request.email is not None:
        update_data["email"] = request.email
    if request.phone is not None:
        update_data["phone"] = request.phone
    if request.avatar is not None:
        update_data["avatar"] = request.avatar
    if request.status is not None:
        update_data["status"] = request.status

    if update_data:
        user = await repo.update_user(user_id, **update_data)

    # 更新角色
    if request.role_ids is not None:
        await repo.set_user_roles(user_id, request.role_ids)

    logger.info(f"User {user.username} updated by {current_user.username}")

    return Result.success(data=user_to_info(user), message="更新成功")


@router.delete("/{user_id}", response_model=Result)
async def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_permission("user:delete")),
    session: AsyncSession = Depends(get_db_session),
):
    """删除用户

    - 超级管理员：可以删除任意用户
    - 业务线管理员：只能删除自己业务线下的用户
    """
    repo = RbacRepository(session)
    user = await repo.get_user_by_id(user_id)

    if not user:
        return Result.not_found("用户不存在")

    # 业务线权限检查
    if not is_super_admin(current_user):
        managed_bl_ids = await get_user_managed_business_line_ids(repo, current_user.id)
        if managed_bl_ids:
            # 检查目标用户是否属于当前用户管理的业务线
            user_roles = await repo.get_user_roles(user_id)
            user_bl_ids = set()
            for role in user_roles:
                if role.business_line_id:
                    user_bl_ids.add(role.business_line_id)
            if not (user_bl_ids & set(managed_bl_ids)):
                return Result.fail(
                    code="403", message="无权删除该用户，该用户不属于您管理的业务线"
                )

    # 不允许删除自己
    if user.id == current_user.id:
        return Result.fail(code="2003", message="不能删除自己")

    await repo.delete_user(user_id)
    logger.info(f"User {user.username} deleted by {current_user.username}")

    return Result.success(message="删除成功")


@router.post("/{user_id}/reset-password", response_model=Result)
async def reset_password(
    user_id: int,
    new_password: str,
    current_user: CurrentUser = Depends(require_permission("user:update")),
    session: AsyncSession = Depends(get_db_session),
):
    """重置用户密码"""
    repo = RbacRepository(session)
    user = await repo.get_user_by_id(user_id)

    if not user:
        return Result.not_found("用户不存在")

    await repo.update_user(user_id, password_hash=hash_password(new_password))
    logger.info(f"Password reset for user {user.username} by {current_user.username}")

    return Result.success(message="密码重置成功")
