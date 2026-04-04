# -*- coding: utf-8 -*-
"""
UserRepository - 用户 CRUD
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import SysUser


class UserRepository(BaseRepository):
    """用户数据访问层"""

    async def get_user_by_id(self, user_id: int) -> Optional[SysUser]:
        """根据ID获取用户"""
        return await self.session.get(SysUser, user_id)

    async def get_user_by_username(self, username: str) -> Optional[SysUser]:
        """根据用户名获取用户"""
        stmt = select(SysUser).where(SysUser.username == username)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_users(self) -> List[SysUser]:
        """获取所有用户"""
        stmt = select(SysUser).order_by(SysUser.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_user(self, user: SysUser) -> SysUser:
        """创建用户"""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: int, **kwargs) -> Optional[SysUser]:
        """更新用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.commit()
        return True

    async def update_user_login_info(self, user_id: int, login_ip: str) -> bool:
        """更新用户登录信息"""
        stmt = (
            update(SysUser)
            .where(SysUser.id == user_id)
            .values(last_login_time=datetime.now(), last_login_ip=login_ip)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True
