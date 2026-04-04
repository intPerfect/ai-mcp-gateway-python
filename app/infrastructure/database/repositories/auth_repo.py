# -*- coding: utf-8 -*-
"""
AuthRepository - 网关Key/认证 CRUD
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import McpGatewayAuth


class AuthRepository(BaseRepository):
    """网关认证数据访问层"""

    async def get_gateway_auth_by_key_id(
        self, gateway_id: str, key_id: str
    ) -> Optional[McpGatewayAuth]:
        """根据gateway_id和key_id获取认证配置（用于bcrypt验证）"""
        stmt = select(McpGatewayAuth).where(
            and_(
                McpGatewayAuth.gateway_id == gateway_id,
                McpGatewayAuth.key_id == key_id,
                McpGatewayAuth.status == 1,
                McpGatewayAuth.expire_time > datetime.now(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_gateway_id_by_api_key(self, api_key: str) -> Optional[str]:
        """通过API Key查找对应的gateway_id"""
        from app.utils.security import parse_api_key

        key_id = parse_api_key(api_key)
        if not key_id:
            return None
        stmt = select(McpGatewayAuth.gateway_id).where(
            and_(
                McpGatewayAuth.key_id == key_id,
                McpGatewayAuth.status == 1,
                McpGatewayAuth.expire_time > datetime.now(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_effective_auth_count(self, gateway_id: str) -> int:
        """获取有效认证数量"""
        stmt = select(McpGatewayAuth).where(
            and_(
                McpGatewayAuth.gateway_id == gateway_id,
                McpGatewayAuth.status == 1,
                McpGatewayAuth.expire_time > datetime.now(),
            )
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def insert_gateway_auth(self, auth: McpGatewayAuth) -> McpGatewayAuth:
        """插入网关认证记录"""
        self.session.add(auth)
        await self.session.commit()
        await self.session.refresh(auth)
        return auth

    async def get_all_gateway_keys(self) -> List[McpGatewayAuth]:
        """获取所有网关Key"""
        stmt = select(McpGatewayAuth).order_by(McpGatewayAuth.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gateway_key_by_id(self, key_id: int) -> Optional[McpGatewayAuth]:
        """根据ID获取网关Key"""
        stmt = select(McpGatewayAuth).where(McpGatewayAuth.id == key_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_gateway_key(self, auth: McpGatewayAuth) -> McpGatewayAuth:
        """创建网关Key"""
        self.session.add(auth)
        await self.session.commit()
        await self.session.refresh(auth)
        return auth

    async def delete_gateway_key(self, key_id: int) -> bool:
        """删除网关Key"""
        key = await self.session.get(McpGatewayAuth, key_id)
        if not key:
            return False
        await self.session.delete(key)
        await self.session.commit()
        return True
