"""
Data Repository for MCP Gateway
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
    """Repository for MCP Gateway data access"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_gateway_by_id(self, gateway_id: str) -> Optional[McpGateway]:
        """Get gateway configuration by gateway_id"""
        stmt = select(McpGateway).where(
            and_(
                McpGateway.gateway_id == gateway_id,
                McpGateway.status == 1
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_gateway_auth_by_api_key(self, gateway_id: str, api_key: str) -> Optional[McpGatewayAuth]:
        """Get auth configuration by gateway_id and api_key"""
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
        """Get gateway auth status"""
        stmt = select(McpGateway.auth).where(McpGateway.gateway_id == gateway_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_effective_auth_count(self, gateway_id: str) -> int:
        """Get count of effective auth records for gateway"""
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
        """Get all tools for a gateway"""
        stmt = select(McpGatewayTool).where(McpGatewayTool.gateway_id == gateway_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_tool_by_name(self, gateway_id: str, tool_name: str) -> Optional[McpGatewayTool]:
        """Get tool by gateway_id and tool_name"""
        stmt = select(McpGatewayTool).where(
            and_(
                McpGatewayTool.gateway_id == gateway_id,
                McpGatewayTool.tool_name == tool_name
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_protocol_http_by_id(self, protocol_id: int) -> Optional[McpProtocolHttp]:
        """Get HTTP protocol configuration by protocol_id"""
        stmt = select(McpProtocolHttp).where(
            and_(
                McpProtocolHttp.protocol_id == protocol_id,
                McpProtocolHttp.status == 1
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_protocol_mappings(self, protocol_id: int, mapping_type: str = "request") -> List[McpProtocolMapping]:
        """Get protocol mappings by protocol_id and type"""
        stmt = select(McpProtocolMapping).where(
            and_(
                McpProtocolMapping.protocol_id == protocol_id,
                McpProtocolMapping.mapping_type == mapping_type
            )
        ).order_by(McpProtocolMapping.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def insert_gateway_auth(self, auth: McpGatewayAuth) -> McpGatewayAuth:
        """Insert new gateway auth record"""
        self.session.add(auth)
        await self.session.commit()
        await self.session.refresh(auth)
        return auth
