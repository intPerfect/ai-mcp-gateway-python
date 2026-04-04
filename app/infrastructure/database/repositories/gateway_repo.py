# -*- coding: utf-8 -*-
"""
GatewayRepository - 网关 CRUD + 网关-微服务绑定
"""

from typing import List, Optional
from sqlalchemy import select, and_, update

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import (
    McpGateway,
    McpGatewayMicroservice,
)


class GatewayRepository(BaseRepository):
    """网关数据访问层"""

    # ============================================
    # 网关管理
    # ============================================

    async def get_gateway_by_id(self, gateway_id: str) -> Optional[McpGateway]:
        """根据gateway_id获取网关配置"""
        stmt = select(McpGateway).where(
            and_(McpGateway.gateway_id == gateway_id, McpGateway.status == 1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_gateways(self) -> List[McpGateway]:
        """获取所有网关"""
        stmt = select(McpGateway).order_by(McpGateway.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gateway_by_numeric_id(self, gateway_id: int) -> Optional[McpGateway]:
        """根据数字ID获取网关"""
        return await self.session.get(McpGateway, gateway_id)

    async def create_gateway(self, gateway: McpGateway) -> McpGateway:
        """创建网关"""
        self.session.add(gateway)
        await self.session.commit()
        await self.session.refresh(gateway)
        return gateway

    async def update_gateway(self, gateway_id: int, **kwargs) -> Optional[McpGateway]:
        """更新网关"""
        stmt = update(McpGateway).where(McpGateway.id == gateway_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_gateway_by_id(kwargs.get("gateway_id", ""))

    async def delete_gateway(self, gateway_id: int) -> bool:
        """删除网关"""
        gateway = await self.session.get(McpGateway, gateway_id)
        if not gateway:
            return False
        await self.session.delete(gateway)
        await self.session.commit()
        return True

    # ============================================
    # 网关-微服务绑定
    # ============================================

    async def get_gateway_microservices(
        self, gateway_id: str
    ) -> List[McpGatewayMicroservice]:
        """获取网关绑定的微服务"""
        stmt = select(McpGatewayMicroservice).where(
            McpGatewayMicroservice.gateway_id == gateway_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bind_microservice_to_gateway(
        self, gateway_id: str, microservice_id: int
    ) -> McpGatewayMicroservice:
        """绑定微服务到网关"""
        binding = McpGatewayMicroservice(
            gateway_id=gateway_id, microservice_id=microservice_id
        )
        self.session.add(binding)
        await self.session.commit()
        await self.session.refresh(binding)
        return binding

    async def unbind_microservice_from_gateway(
        self, gateway_id: str, microservice_id: int
    ) -> bool:
        """解绑微服务"""
        stmt = select(McpGatewayMicroservice).where(
            and_(
                McpGatewayMicroservice.gateway_id == gateway_id,
                McpGatewayMicroservice.microservice_id == microservice_id,
            )
        )
        result = await self.session.execute(stmt)
        binding = result.scalars().first()
        if binding:
            await self.session.delete(binding)
            await self.session.commit()
        return True

    async def set_gateway_microservices(
        self, gateway_id: str, microservice_ids: List[int]
    ) -> bool:
        """设置网关绑定的微服务（覆盖）"""
        # 删除原有绑定
        stmt = select(McpGatewayMicroservice).where(
            McpGatewayMicroservice.gateway_id == gateway_id
        )
        result = await self.session.execute(stmt)
        for binding in result.scalars().all():
            await self.session.delete(binding)
        # 添加新绑定
        for ms_id in microservice_ids:
            binding = McpGatewayMicroservice(
                gateway_id=gateway_id, microservice_id=ms_id
            )
            self.session.add(binding)
        await self.session.commit()
        return True
