# -*- coding: utf-8 -*-
"""
MicroserviceRepository - 微服务 CRUD
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import McpMicroservice


class MicroserviceRepository(BaseRepository):
    """微服务数据访问层"""

    async def get_all_microservices(self) -> List[McpMicroservice]:
        """获取所有微服务"""
        stmt = select(McpMicroservice).order_by(McpMicroservice.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_microservice_by_id(
        self, microservice_id: int
    ) -> Optional[McpMicroservice]:
        """根据ID获取微服务"""
        stmt = select(McpMicroservice).where(McpMicroservice.id == microservice_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_microservice_by_name(self, name: str) -> Optional[McpMicroservice]:
        """根据名称获取微服务"""
        stmt = select(McpMicroservice).where(McpMicroservice.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_microservice(
        self, microservice: McpMicroservice
    ) -> McpMicroservice:
        """创建微服务"""
        self.session.add(microservice)
        await self.session.commit()
        await self.session.refresh(microservice)
        return microservice

    async def update_microservice(
        self, microservice_id: int, **kwargs
    ) -> Optional[McpMicroservice]:
        """更新微服务"""
        microservice = await self.get_microservice_by_id(microservice_id)
        if not microservice:
            return None
        for key, value in kwargs.items():
            if hasattr(microservice, key) and value is not None:
                setattr(microservice, key, value)
        await self.session.commit()
        await self.session.refresh(microservice)
        return microservice

    async def delete_microservice(self, microservice_id: int) -> bool:
        """删除微服务"""
        microservice = await self.get_microservice_by_id(microservice_id)
        if not microservice:
            return False
        await self.session.delete(microservice)
        await self.session.commit()
        return True

    async def update_microservice_health(
        self, microservice_id: int, health_status: str
    ) -> bool:
        """更新微服务健康状态"""
        stmt = (
            update(McpMicroservice)
            .where(McpMicroservice.id == microservice_id)
            .values(health_status=health_status, last_check_time=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True
