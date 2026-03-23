"""
Data Repository for MCP Gateway v3.0
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.models import (
    McpGateway,
    McpGatewayAuth,
    McpGatewayTool,
    McpProtocolHttp,
    McpProtocolMapping
)


class McpGatewayRepository:
    """MCP网关数据访问层"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_gateway_by_id(self, gateway_id: str) -> Optional[McpGateway]:
        """根据gateway_id获取网关配置"""
        stmt = select(McpGateway).where(
            and_(
                McpGateway.gateway_id == gateway_id,
                McpGateway.status == 1
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_gateway_auth_by_api_key(self, gateway_id: str, api_key: str) -> Optional[McpGatewayAuth]:
        """根据gateway_id和api_key获取认证配置"""
        stmt = select(McpGatewayAuth).where(
            and_(
                McpGatewayAuth.gateway_id == gateway_id,
                McpGatewayAuth.api_key == api_key,
                McpGatewayAuth.status == 1,
                McpGatewayAuth.expire_time > datetime.now()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_gateway_auth_status(self, gateway_id: str) -> Optional[int]:
        """获取网关认证状态"""
        stmt = select(McpGateway.auth).where(McpGateway.gateway_id == gateway_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_effective_auth_count(self, gateway_id: str) -> int:
        """获取有效认证数量"""
        stmt = select(McpGatewayAuth).where(
            and_(
                McpGatewayAuth.gateway_id == gateway_id,
                McpGatewayAuth.status == 1,
                McpGatewayAuth.expire_time > datetime.now()
            )
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
    
    async def get_tools_by_gateway_id(self, gateway_id: str) -> List[McpGatewayTool]:
        """获取网关所有工具"""
        stmt = select(McpGatewayTool).where(McpGatewayTool.gateway_id == gateway_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_tool_by_name(self, gateway_id: str, tool_name: str) -> Optional[McpGatewayTool]:
        """根据名称获取工具"""
        stmt = select(McpGatewayTool).where(
            and_(
                McpGatewayTool.gateway_id == gateway_id,
                McpGatewayTool.tool_name == tool_name
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_protocol_http_by_id(self, protocol_id: int) -> Optional[McpProtocolHttp]:
        """根据protocol_id获取HTTP协议配置"""
        stmt = select(McpProtocolHttp).where(
            and_(
                McpProtocolHttp.protocol_id == protocol_id,
                McpProtocolHttp.status == 1
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_protocol_mappings(self, protocol_id: int) -> List[McpProtocolMapping]:
        """获取协议的所有参数映射"""
        stmt = select(McpProtocolMapping).where(
            McpProtocolMapping.protocol_id == protocol_id
        ).order_by(McpProtocolMapping.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_protocol_mappings_by_location(
        self, 
        protocol_id: int, 
        param_location: str
    ) -> List[McpProtocolMapping]:
        """
        根据参数位置获取映射
        
        param_location: path/query/body/form/header/file
        """
        stmt = select(McpProtocolMapping).where(
            and_(
                McpProtocolMapping.protocol_id == protocol_id,
                McpProtocolMapping.param_location == param_location
            )
        ).order_by(McpProtocolMapping.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def insert_gateway_auth(self, auth: McpGatewayAuth) -> McpGatewayAuth:
        """插入网关认证记录"""
        self.session.add(auth)
        await self.session.commit()
        await self.session.refresh(auth)
        return auth