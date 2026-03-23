# -*- coding: utf-8 -*-
"""
Database Repository - 数据仓库
数据访问层，封装数据库操作
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    McpGateway,
    McpGatewayAuth,
    McpGatewayTool,
    McpProtocolHttp,
    McpProtocolMapping,
    McpMicroservice,
    McpLlm,
    McpLlmKey
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
    
    async def get_gateway_auth_by_key_id(self, gateway_id: str, key_id: str) -> Optional[McpGatewayAuth]:
        """根据gateway_id和key_id获取认证配置（用于bcrypt验证）"""
        stmt = select(McpGatewayAuth).where(
            and_(
                McpGatewayAuth.gateway_id == gateway_id,
                McpGatewayAuth.key_id == key_id,
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
    
    # ============================================
    # 微服务管理方法
    # ============================================
    
    async def get_all_microservices(self) -> List[McpMicroservice]:
        """获取所有微服务"""
        stmt = select(McpMicroservice).order_by(McpMicroservice.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_microservice_by_id(self, microservice_id: int) -> Optional[McpMicroservice]:
        """根据ID获取微服务"""
        stmt = select(McpMicroservice).where(McpMicroservice.id == microservice_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def get_microservice_by_name(self, name: str) -> Optional[McpMicroservice]:
        """根据名称获取微服务"""
        stmt = select(McpMicroservice).where(McpMicroservice.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def create_microservice(self, microservice: McpMicroservice) -> McpMicroservice:
        """创建微服务"""
        self.session.add(microservice)
        await self.session.commit()
        await self.session.refresh(microservice)
        return microservice
    
    async def update_microservice(self, microservice_id: int, **kwargs) -> Optional[McpMicroservice]:
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
    
    async def update_microservice_health(self, microservice_id: int, health_status: str) -> bool:
        """更新微服务健康状态"""
        stmt = (
            update(McpMicroservice)
            .where(McpMicroservice.id == microservice_id)
            .values(health_status=health_status, last_check_time=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True
    
    # ============================================
    # 工具管理方法
    # ============================================
    
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
    
    async def get_tools_by_microservice(self, microservice_id: int) -> List[McpGatewayTool]:
        """获取微服务下的工具"""
        stmt = select(McpGatewayTool).where(
            McpGatewayTool.microservice_id == microservice_id
        ).order_by(McpGatewayTool.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_unbind_tools(self) -> List[McpGatewayTool]:
        """获取未绑定微服务的工具"""
        stmt = select(McpGatewayTool).where(
            McpGatewayTool.microservice_id.is_(None)
        ).order_by(McpGatewayTool.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def bind_tool_to_microservice(self, tool_id: int, microservice_id: int) -> bool:
        """绑定工具到微服务"""
        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(microservice_id=microservice_id)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True
    
    async def unbind_tool(self, tool_id: int) -> bool:
        """解绑工具"""
        stmt = (
            update(McpGatewayTool)
            .where(McpGatewayTool.tool_id == tool_id)
            .values(microservice_id=None)
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
    
    async def update_tool_call_status(
        self, 
        tool_id: int, 
        call_status: str, 
        call_code: str = None,
        is_error: bool = False
    ) -> bool:
        """更新工具调用状态"""
        tool = await self.get_tool_by_id(tool_id)
        if not tool:
            return False
        
        values = {
            "call_status": call_status,
            "last_call_time": datetime.now(),
            "call_count": (tool.call_count or 0) + 1
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
    # 网关管理方法
    # ============================================

    async def get_all_gateways(self) -> List[McpGateway]:
        """获取所有网关"""
        stmt = select(McpGateway).order_by(McpGateway.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_gateway(self, gateway: McpGateway) -> McpGateway:
        """创建网关"""
        self.session.add(gateway)
        await self.session.commit()
        await self.session.refresh(gateway)
        return gateway

    async def update_gateway(self, gateway_id: int, **kwargs) -> Optional[McpGateway]:
        """更新网关"""
        stmt = (
            update(McpGateway)
            .where(McpGateway.id == gateway_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_gateway_by_id(kwargs.get('gateway_id', ''))

    async def delete_gateway(self, gateway_id: int) -> bool:
        """删除网关"""
        gateway = await self.session.get(McpGateway, gateway_id)
        if not gateway:
            return False
        await self.session.delete(gateway)
        await self.session.commit()
        return True

    # ============================================
    # 网关Key管理方法
    # ============================================

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

    # ============================================
    # LLM管理方法
    # ============================================

    async def get_all_llms(self) -> List[McpLlm]:
        """获取所有LLM配置"""
        stmt = select(McpLlm).order_by(McpLlm.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_llm_by_id(self, llm_id: int) -> Optional[McpLlm]:
        """根据ID获取LLM配置"""
        stmt = select(McpLlm).where(McpLlm.id == llm_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_llm_by_llm_id(self, llm_id: str) -> Optional[McpLlm]:
        """根据llm_id字符串获取LLM配置"""
        stmt = select(McpLlm).where(McpLlm.llm_id == llm_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_llm(self, llm: McpLlm) -> McpLlm:
        """创建LLM配置"""
        self.session.add(llm)
        await self.session.commit()
        await self.session.refresh(llm)
        return llm

    async def update_llm(self, llm_id: int, **kwargs) -> Optional[McpLlm]:
        """更新LLM配置"""
        stmt = (
            update(McpLlm)
            .where(McpLlm.id == llm_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_llm_by_id(llm_id)

    async def delete_llm(self, llm_id: int) -> bool:
        """删除LLM配置"""
        llm = await self.session.get(McpLlm, llm_id)
        if not llm:
            return False
        await self.session.delete(llm)
        await self.session.commit()
        return True

    # ============================================
    # LLM Key管理方法
    # ============================================

    async def get_all_llm_keys(self) -> List[McpLlmKey]:
        """获取所有LLM Key"""
        stmt = select(McpLlmKey).order_by(McpLlmKey.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_llm_key_by_id(self, key_id: int) -> Optional[McpLlmKey]:
        """根据ID获取LLM Key"""
        stmt = select(McpLlmKey).where(McpLlmKey.id == key_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_llm_key_by_key_id(self, key_id: str) -> Optional[McpLlmKey]:
        """根据key_id字符串获取LLM Key"""
        stmt = select(McpLlmKey).where(McpLlmKey.key_id == key_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_llm_key(self, llm_key: McpLlmKey) -> McpLlmKey:
        """创建LLM Key"""
        self.session.add(llm_key)
        await self.session.commit()
        await self.session.refresh(llm_key)
        return llm_key

    async def delete_llm_key(self, key_id: int) -> bool:
        """删除LLM Key"""
        key = await self.session.get(McpLlmKey, key_id)
        if not key:
            return False
        await self.session.delete(key)
        await self.session.commit()
        return True
