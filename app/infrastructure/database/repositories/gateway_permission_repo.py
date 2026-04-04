# -*- coding: utf-8 -*-
"""
GatewayPermissionRepository - 网关权限管理
"""

from typing import List, Optional
from sqlalchemy import select, and_

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import SysGatewayPermission


class GatewayPermissionRepository(BaseRepository):
    """网关权限数据访问层"""

    async def get_gateway_permissions_by_role(
        self, role_id: int
    ) -> List[SysGatewayPermission]:
        """获取角色的所有网关权限"""
        stmt = select(SysGatewayPermission).where(
            SysGatewayPermission.role_id == role_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gateway_permission(
        self, role_id: int, gateway_id: str
    ) -> Optional[SysGatewayPermission]:
        """获取角色对指定网关的权限"""
        stmt = select(SysGatewayPermission).where(
            and_(
                SysGatewayPermission.role_id == role_id,
                SysGatewayPermission.gateway_id == gateway_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def set_gateway_permission(
        self,
        role_id: int,
        gateway_id: str,
        can_create: bool = False,
        can_read: bool = False,
        can_update: bool = False,
        can_delete: bool = False,
        can_chat: bool = False,
    ) -> SysGatewayPermission:
        """设置角色对网关的权限"""
        existing = await self.get_gateway_permission(role_id, gateway_id)
        if existing:
            existing.can_create = 1 if can_create else 0
            existing.can_read = 1 if can_read else 0
            existing.can_update = 1 if can_update else 0
            existing.can_delete = 1 if can_delete else 0
            existing.can_chat = 1 if can_chat else 0
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            perm = SysGatewayPermission(
                role_id=role_id,
                gateway_id=gateway_id,
                can_create=1 if can_create else 0,
                can_read=1 if can_read else 0,
                can_update=1 if can_update else 0,
                can_delete=1 if can_delete else 0,
                can_chat=1 if can_chat else 0,
            )
            self.session.add(perm)
            await self.session.commit()
            await self.session.refresh(perm)
            return perm

    async def delete_gateway_permissions_by_role(self, role_id: int) -> bool:
        """删除角色的所有网关权限"""
        stmt = select(SysGatewayPermission).where(
            SysGatewayPermission.role_id == role_id
        )
        result = await self.session.execute(stmt)
        for gp in result.scalars().all():
            await self.session.delete(gp)
        await self.session.commit()
        return True

    async def _upsert_gateway_permission(self, role_id: int, perm: dict) -> None:
        """单条网关权限 upsert：相同跳过、不存在新增、存在但不同则更新"""
        new_vals = {
            "can_create": 1 if perm.get("can_create", False) else 0,
            "can_read": 1 if perm.get("can_read", False) else 0,
            "can_update": 1 if perm.get("can_update", False) else 0,
            "can_delete": 1 if perm.get("can_delete", False) else 0,
            "can_chat": 1 if perm.get("can_chat", False) else 0,
        }
        existing = await self.get_gateway_permission(role_id, perm["gateway_id"])
        if existing:
            for k, v in new_vals.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
        else:
            gp = SysGatewayPermission(
                role_id=role_id,
                gateway_id=perm["gateway_id"],
                **new_vals,
            )
            self.session.add(gp)

    async def set_role_gateway_permissions(
        self, role_id: int, permissions: List[dict]
    ) -> bool:
        """批量设置角色的网关权限（全量覆盖）"""
        existing_perms = await self.get_gateway_permissions_by_role(role_id)
        existing_map = {p.gateway_id: p for p in existing_perms}
        incoming_ids = {p["gateway_id"] for p in permissions}

        # 删除不在新列表中的权限
        for gw_id, gp in existing_map.items():
            if gw_id not in incoming_ids:
                await self.session.delete(gp)

        # upsert 每条权限
        for perm in permissions:
            await self._upsert_gateway_permission(role_id, perm)

        await self.session.commit()
        return True

    async def set_role_gateway_permissions_scoped(
        self, role_id: int, permissions: List[dict], scoped_gateway_ids: List[str]
    ) -> bool:
        """按范围设置角色的网关权限（仅更新指定网关范围内的权限，保留范围外不变）"""
        incoming_ids = {p["gateway_id"] for p in permissions}

        # 仅删除范围内、但不在新列表中的权限
        for gw_id in scoped_gateway_ids:
            if gw_id not in incoming_ids:
                existing = await self.get_gateway_permission(role_id, gw_id)
                if existing:
                    await self.session.delete(existing)

        # upsert 每条权限
        for perm in permissions:
            await self._upsert_gateway_permission(role_id, perm)

        await self.session.commit()
        return True
