# -*- coding: utf-8 -*-
"""
ToolRepository - 工具 CRUD + 协议配置
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, update

from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.models import (
    McpGatewayTool,
    McpProtocolHttp,
    McpProtocolMapping,
)


class ToolRepository(BaseRepository):
    """工具数据访问层"""

    # ============================================
    # 工具查询
    # ============================================

    async def get_tools_by_gateway_id(
        self, gateway_id: str = None
    ) -> List[McpGatewayTool]:
        """获取网关所有工具，如果 gateway_id 为 None 则返回所有工具"""
        if gateway_id:
            stmt = select(McpGatewayTool).where(McpGatewayTool.gateway_id == gateway_id)
        else:
            stmt = select(McpGatewayTool)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tool_by_name(
        self, gateway_id: str, tool_name: str
    ) -> Optional[McpGatewayTool]:
        """根据名称获取工具"""
        stmt = select(McpGatewayTool).where(
            and_(
                McpGatewayTool.gateway_id == gateway_id,
                McpGatewayTool.tool_name == tool_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_tools(self) -> List[McpGatewayTool]:
        """获取所有工具"""
        stmt = select(McpGatewayTool).order_by(McpGatewayTool.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tool_by_id(self, tool_id: int) -> Optional[McpGatewayTool]:
        """根据ID获取工具"""
        stmt = select(McpGatewayTool).where(McpGatewayTool.tool_id == tool_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_tools_by_microservice(
        self, microservice_id: int
    ) -> List[McpGatewayTool]:
        """获取微服务下的工具"""
        stmt = (
            select(McpGatewayTool)
            .where(McpGatewayTool.microservice_id == microservice_id)
            .order_by(McpGatewayTool.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ============================================
    # 工具修改
    # ============================================

    async def bind_tool_to_microservice(
        self, tool_id: int, microservice_id: int
    ) -> bool:
        """绑定工具到微服务"""
        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(microservice_id=microservice_id)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_tool_enabled(self, tool_id: int, enabled: int) -> bool:
        """更新工具启用状态"""
        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(enabled=enabled)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_tool(self, tool_id: int, **kwargs) -> bool:
        """更新工具信息"""
        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def update_tool_call_status(
        self,
        tool_id: int,
        call_status: str,
        call_code: str = None,
        is_error: bool = False,
    ) -> bool:
        """更新工具调用状态"""
        tool = await self.get_tool_by_id(tool_id)
        if not tool:
            return False

        values = {
            "call_status": call_status,
            "last_call_time": datetime.now(),
            "call_count": (tool.call_count or 0) + 1,
        }
        if call_code:
            values["last_call_code"] = call_code
        if is_error:
            values["error_count"] = (tool.error_count or 0) + 1

        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    # ============================================
    # 协议配置
    # ============================================

    async def get_protocol_http_by_id(
        self, protocol_id: int
    ) -> Optional[McpProtocolHttp]:
        """根据protocol_id获取HTTP协议配置"""
        stmt = select(McpProtocolHttp).where(
            and_(
                McpProtocolHttp.protocol_id == protocol_id, McpProtocolHttp.status == 1
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_protocol_mappings(self, protocol_id: int) -> List[McpProtocolMapping]:
        """获取协议的所有参数映射"""
        stmt = (
            select(McpProtocolMapping)
            .where(McpProtocolMapping.protocol_id == protocol_id)
            .order_by(McpProtocolMapping.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_protocol_mappings_by_location(
        self, protocol_id: int, param_location: str
    ) -> List[McpProtocolMapping]:
        """根据参数位置获取映射"""
        stmt = (
            select(McpProtocolMapping)
            .where(
                and_(
                    McpProtocolMapping.protocol_id == protocol_id,
                    McpProtocolMapping.param_location == param_location,
                )
            )
            .order_by(McpProtocolMapping.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_protocol_http(self, protocol_id: int, **kwargs) -> bool:
        """更新HTTP协议配置"""
        stmt = (
            update(McpProtocolHttp)
            .where(McpProtocolHttp.protocol_id == protocol_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def delete_protocol_mappings(self, protocol_id: int) -> bool:
        """删除协议的所有参数映射"""
        stmt = select(McpProtocolMapping).where(
            McpProtocolMapping.protocol_id == protocol_id
        )
        result = await self.session.execute(stmt)
        for mapping in result.scalars().all():
            await self.session.delete(mapping)
        await self.session.commit()
        return True

    async def create_protocol_mapping(
        self, mapping: McpProtocolMapping
    ) -> McpProtocolMapping:
        """创建参数映射"""
        self.session.add(mapping)
        await self.session.commit()
        await self.session.refresh(mapping)
        return mapping

    async def batch_create_protocol_mappings(
        self, mappings: list[McpProtocolMapping]
    ) -> bool:
        """批量创建参数映射"""
        for mapping in mappings:
            self.session.add(mapping)
        await self.session.commit()
        return True
