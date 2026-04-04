# -*- coding: utf-8 -*-
"""
LlmConfigRepository - LLM配置 + 网关-LLM绑定 CRUD
"""

from typing import List, Optional
from sqlalchemy import select, and_, update

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import (
    McpLlmConfig,
    McpGatewayLlm,
)


class LlmConfigRepository(BaseRepository):
    """LLM配置数据访问层"""

    # ============================================
    # LLM 配置管理
    # ============================================

    async def get_all_llm_configs(self) -> List[McpLlmConfig]:
        """获取所有LLM配置"""
        stmt = select(McpLlmConfig).order_by(McpLlmConfig.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_llm_config_by_id(self, config_id: int) -> Optional[McpLlmConfig]:
        """根据ID获取LLM配置"""
        stmt = select(McpLlmConfig).where(McpLlmConfig.id == config_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_llm_config_by_config_id(
        self, config_id: str
    ) -> Optional[McpLlmConfig]:
        """根据config_id字符串获取LLM配置"""
        stmt = select(McpLlmConfig).where(McpLlmConfig.config_id == config_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_llm_config(self, llm_config: McpLlmConfig) -> McpLlmConfig:
        """创建LLM配置"""
        self.session.add(llm_config)
        await self.session.commit()
        await self.session.refresh(llm_config)
        return llm_config

    async def update_llm_config(
        self, config_id: int, **kwargs
    ) -> Optional[McpLlmConfig]:
        """更新LLM配置"""
        stmt = update(McpLlmConfig).where(McpLlmConfig.id == config_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_llm_config_by_id(config_id)

    async def delete_llm_config(self, config_id: int) -> bool:
        """删除LLM配置"""
        llm_config = await self.session.get(McpLlmConfig, config_id)
        if not llm_config:
            return False
        await self.session.delete(llm_config)
        await self.session.commit()
        return True

    # ============================================
    # 网关-LLM绑定
    # ============================================

    async def get_gateway_llms(self, gateway_id: str) -> List[McpGatewayLlm]:
        """获取网关绑定的LLM"""
        stmt = select(McpGatewayLlm).where(
            and_(McpGatewayLlm.gateway_id == gateway_id, McpGatewayLlm.status == 1)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gateway_llm_configs(self, gateway_id: str) -> List[McpLlmConfig]:
        """获取网关绑定的LLM配置列表"""
        stmt = (
            select(McpLlmConfig)
            .join(McpGatewayLlm, McpLlmConfig.config_id == McpGatewayLlm.llm_config_id)
            .where(
                and_(
                    McpGatewayLlm.gateway_id == gateway_id,
                    McpGatewayLlm.status == 1,
                    McpLlmConfig.status == 1,
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bind_llm_to_gateway(
        self, gateway_id: str, llm_config_id: str
    ) -> McpGatewayLlm:
        """绑定LLM到网关"""
        binding = McpGatewayLlm(gateway_id=gateway_id, llm_config_id=llm_config_id)
        self.session.add(binding)
        await self.session.commit()
        await self.session.refresh(binding)
        return binding

    async def unbind_llm_from_gateway(
        self, gateway_id: str, llm_config_id: str
    ) -> bool:
        """解绑LLM"""
        stmt = select(McpGatewayLlm).where(
            and_(
                McpGatewayLlm.gateway_id == gateway_id,
                McpGatewayLlm.llm_config_id == llm_config_id,
            )
        )
        result = await self.session.execute(stmt)
        binding = result.scalars().first()
        if binding:
            await self.session.delete(binding)
            await self.session.commit()
        return True

    async def is_llm_bound_to_gateway(
        self, gateway_id: str, llm_config_id: str
    ) -> bool:
        """检查LLM是否绑定到网关"""
        stmt = select(McpGatewayLlm).where(
            and_(
                McpGatewayLlm.gateway_id == gateway_id,
                McpGatewayLlm.llm_config_id == llm_config_id,
                McpGatewayLlm.status == 1,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None
