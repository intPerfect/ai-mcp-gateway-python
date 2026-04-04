# -*- coding: utf-8 -*-
"""
RoleRepository - 角色 + 用户角色关联
"""

from typing import List, Optional
from sqlalchemy import select, and_

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import SysRole, SysUserRole


class RoleRepository(BaseRepository):
    """角色数据访问层"""

    # ============================================
    # 角色管理
    # ============================================

    async def get_role_by_id(self, role_id: int) -> Optional[SysRole]:
        """根据ID获取角色"""
        return await self.session.get(SysRole, role_id)

    async def get_role_by_code(self, role_code: str) -> Optional[SysRole]:
        """根据角色编码获取角色"""
        stmt = select(SysRole).where(SysRole.role_code == role_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_roles(self) -> List[SysRole]:
        """获取所有角色"""
        stmt = select(SysRole).order_by(SysRole.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_role(self, role: SysRole) -> SysRole:
        """创建角色"""
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update_role(self, role_id: int, **kwargs) -> Optional[SysRole]:
        """更新角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        for key, value in kwargs.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        await self.session.delete(role)
        await self.session.commit()
        return True

    # ============================================
    # 用户角色关联
    # ============================================

    async def get_user_roles(self, user_id: int) -> List[SysRole]:
        """获取用户的所有角色"""
        stmt = (
            select(SysRole)
            .join(SysUserRole, SysRole.id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """给用户分配角色"""
        user_role = SysUserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.commit()
        return True

    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """移除用户角色"""
        stmt = select(SysUserRole).where(
            and_(SysUserRole.user_id == user_id, SysUserRole.role_id == role_id)
        )
        result = await self.session.execute(stmt)
        user_role = result.scalars().first()
        if user_role:
            await self.session.delete(user_role)
            await self.session.commit()
        return True

    async def set_user_roles(self, user_id: int, role_ids: List[int]) -> bool:
        """设置用户角色（覆盖）"""
        # 删除原有角色
        stmt = select(SysUserRole).where(SysUserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        for ur in result.scalars().all():
            await self.session.delete(ur)
        # 添加新角色
        for role_id in role_ids:
            user_role = SysUserRole(user_id=user_id, role_id=role_id)
            self.session.add(user_role)
        await self.session.commit()
        return True
