# -*- coding: utf-8 -*-
"""
PermissionRepository - 权限/资源查询 + 登录日志
"""

from typing import List, Optional
from sqlalchemy import select, and_

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import (
    SysPermission,
    SysRolePermission,
    SysUserRole,
    SysResource,
    SysLoginLog,
)


class PermissionRepository(BaseRepository):
    """权限数据访问层"""

    # ============================================
    # 权限管理
    # ============================================

    async def get_permission_by_id(self, permission_id: int) -> Optional[SysPermission]:
        """根据ID获取权限"""
        return await self.session.get(SysPermission, permission_id)

    async def get_permission_by_code(
        self, permission_code: str
    ) -> Optional[SysPermission]:
        """根据权限编码获取权限"""
        stmt = select(SysPermission).where(
            SysPermission.permission_code == permission_code
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_permissions(self) -> List[SysPermission]:
        """获取所有权限"""
        stmt = select(SysPermission).order_by(
            SysPermission.resource_id, SysPermission.action
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_resource(
        self, resource_id: int
    ) -> List[SysPermission]:
        """获取资源的所有权限"""
        stmt = select(SysPermission).where(SysPermission.resource_id == resource_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_role_permissions(self, role_id: int) -> List[SysPermission]:
        """获取角色的所有权限"""
        stmt = (
            select(SysPermission)
            .join(
                SysRolePermission, SysPermission.id == SysRolePermission.permission_id
            )
            .where(SysRolePermission.role_id == role_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_permissions(self, user_id: int) -> List[SysPermission]:
        """获取用户的所有权限（通过角色）"""
        stmt = (
            select(SysPermission)
            .distinct()
            .join(
                SysRolePermission, SysPermission.id == SysRolePermission.permission_id
            )
            .join(SysUserRole, SysRolePermission.role_id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """给角色分配权限"""
        role_perm = SysRolePermission(role_id=role_id, permission_id=permission_id)
        self.session.add(role_perm)
        await self.session.commit()
        return True

    async def remove_permission_from_role(
        self, role_id: int, permission_id: int
    ) -> bool:
        """移除角色权限"""
        stmt = select(SysRolePermission).where(
            and_(
                SysRolePermission.role_id == role_id,
                SysRolePermission.permission_id == permission_id,
            )
        )
        result = await self.session.execute(stmt)
        role_perm = result.scalars().first()
        if role_perm:
            await self.session.delete(role_perm)
            await self.session.commit()
        return True

    async def set_role_permissions(
        self, role_id: int, permission_ids: List[int]
    ) -> bool:
        """设置角色权限（覆盖）"""
        # 删除原有权限
        stmt = select(SysRolePermission).where(SysRolePermission.role_id == role_id)
        result = await self.session.execute(stmt)
        for rp in result.scalars().all():
            await self.session.delete(rp)
        # 添加新权限
        for perm_id in permission_ids:
            role_perm = SysRolePermission(role_id=role_id, permission_id=perm_id)
            self.session.add(role_perm)
        await self.session.commit()
        return True

    # ============================================
    # 资源管理
    # ============================================

    async def get_all_resources(self) -> List[SysResource]:
        """获取所有资源"""
        stmt = select(SysResource).order_by(SysResource.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_resource_by_id(self, resource_id: int) -> Optional[SysResource]:
        """根据ID获取资源"""
        return await self.session.get(SysResource, resource_id)

    # ============================================
    # 登录日志
    # ============================================

    async def create_login_log(self, log: SysLoginLog) -> SysLoginLog:
        """创建登录日志"""
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_login_logs(self, limit: int = 100) -> List[SysLoginLog]:
        """获取登录日志"""
        stmt = select(SysLoginLog).order_by(SysLoginLog.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
