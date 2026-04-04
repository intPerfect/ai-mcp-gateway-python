# -*- coding: utf-8 -*-
"""
BusinessLineRepository - 业务线 + 用户业务线关联 + 角色业务线管理员
"""

from typing import List, Optional
from sqlalchemy import select, and_

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import (
    SysBusinessLine,
    SysUserBusinessLine,
    SysRoleBusinessLine,
)


class BusinessLineRepository(BaseRepository):
    """业务线数据访问层"""

    # ============================================
    # 业务线管理
    # ============================================

    async def get_business_line_by_id(self, bl_id: int) -> Optional[SysBusinessLine]:
        """根据ID获取业务线"""
        return await self.session.get(SysBusinessLine, bl_id)

    async def get_business_line_by_code(
        self, line_code: str
    ) -> Optional[SysBusinessLine]:
        """根据编码获取业务线"""
        stmt = select(SysBusinessLine).where(SysBusinessLine.line_code == line_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_business_lines(self) -> List[SysBusinessLine]:
        """获取所有业务线"""
        stmt = select(SysBusinessLine).order_by(SysBusinessLine.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_business_lines(self) -> List[SysBusinessLine]:
        """获取所有启用的业务线（status=1）"""
        stmt = (
            select(SysBusinessLine)
            .where(SysBusinessLine.status == 1)
            .order_by(SysBusinessLine.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_business_line(self, bl: SysBusinessLine) -> SysBusinessLine:
        """创建业务线"""
        self.session.add(bl)
        await self.session.commit()
        await self.session.refresh(bl)
        return bl

    async def update_business_line(
        self, bl_id: int, **kwargs
    ) -> Optional[SysBusinessLine]:
        """更新业务线"""
        bl = await self.get_business_line_by_id(bl_id)
        if not bl:
            return None
        for key, value in kwargs.items():
            if hasattr(bl, key) and value is not None:
                setattr(bl, key, value)
        await self.session.commit()
        await self.session.refresh(bl)
        return bl

    async def delete_business_line(self, bl_id: int) -> bool:
        """删除业务线"""
        bl = await self.get_business_line_by_id(bl_id)
        if not bl:
            return False
        await self.session.delete(bl)
        await self.session.commit()
        return True

    # ============================================
    # 用户-业务线关联
    # ============================================

    async def get_user_business_lines(self, user_id: int) -> List[SysUserBusinessLine]:
        """获取用户的所有业务线关联"""
        stmt = select(SysUserBusinessLine).where(SysUserBusinessLine.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_managed_business_lines(
        self, user_id: int
    ) -> List[SysUserBusinessLine]:
        """获取用户管理的业务线（is_admin=1）"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_business_line_users(self, bl_id: int) -> List[SysUserBusinessLine]:
        """获取业务线下的所有用户"""
        stmt = select(SysUserBusinessLine).where(
            SysUserBusinessLine.business_line_id == bl_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_user_to_business_line(
        self, user_id: int, bl_id: int, is_admin: bool = False
    ) -> SysUserBusinessLine:
        """添加用户到业务线"""
        ubl = SysUserBusinessLine(
            user_id=user_id, business_line_id=bl_id, is_admin=1 if is_admin else 0
        )
        self.session.add(ubl)
        await self.session.commit()
        await self.session.refresh(ubl)
        return ubl

    async def remove_user_from_business_line(self, user_id: int, bl_id: int) -> bool:
        """从业务线移除用户"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        ubl = result.scalars().first()
        if ubl:
            await self.session.delete(ubl)
            await self.session.commit()
        return True

    async def set_user_business_line_admin(
        self, user_id: int, bl_id: int, is_admin: bool
    ) -> bool:
        """设置用户在业务线的管理员权限"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        ubl = result.scalars().first()
        if ubl:
            ubl.is_admin = 1 if is_admin else 0
            await self.session.commit()
            return True
        return False

    async def is_business_line_admin(self, user_id: int, bl_id: int) -> bool:
        """检查用户是否是某业务线管理员"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
                SysUserBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def is_user_in_business_line(self, user_id: int, bl_id: int) -> bool:
        """检查用户是否属于某业务线"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    # ============================================
    # 角色-业务线管理员
    # ============================================

    async def get_role_bl_admin_ids(self, role_id: int) -> List[int]:
        """获取角色作为管理员的业务线ID列表"""
        stmt = select(SysRoleBusinessLine).where(
            and_(
                SysRoleBusinessLine.role_id == role_id,
                SysRoleBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return [r.business_line_id for r in result.scalars().all()]

    async def set_role_bl_admin_ids(
        self, role_id: int, bl_ids: List[int]
    ) -> bool:
        """设置角色的业务线管理员权限（upsert）"""
        stmt = select(SysRoleBusinessLine).where(
            SysRoleBusinessLine.role_id == role_id
        )
        result = await self.session.execute(stmt)
        existing = {r.business_line_id: r for r in result.scalars().all()}
        incoming = set(bl_ids)

        # 删除不在新列表中的记录
        for bl_id, record in existing.items():
            if bl_id not in incoming:
                await self.session.delete(record)

        # 新增不存在的记录
        for bl_id in incoming:
            if bl_id not in existing:
                rbl = SysRoleBusinessLine(
                    role_id=role_id,
                    business_line_id=bl_id,
                    is_admin=1,
                )
                self.session.add(rbl)

        await self.session.commit()
        return True

    async def get_role_bl_admin_ids_for_user(
        self, role_ids: List[int]
    ) -> List[int]:
        """获取一组角色授予管理员权限的所有业务线ID（去重）"""
        if not role_ids:
            return []
        stmt = select(SysRoleBusinessLine.business_line_id).where(
            and_(
                SysRoleBusinessLine.role_id.in_(role_ids),
                SysRoleBusinessLine.is_admin == 1,
            )
        ).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
