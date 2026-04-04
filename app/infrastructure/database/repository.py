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
    McpLlmConfig,
    McpGatewayLlm,
    McpGatewayMicroservice,
    # RBAC models
    SysUser,
    SysRole,
    SysUserRole,
    SysResource,
    SysPermission,
    SysRolePermission,
    SysGatewayPermission,
    SysRoleBusinessLine,
    SysLoginLog,
    # Business Line models (v8.0)
    SysBusinessLine,
    SysUserBusinessLine,
)


class McpGatewayRepository:
    """MCP网关数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================
    # 业务线管理 (v8.0) - 委托给 session
    # ============================================

    async def get_all_business_lines(self) -> List[SysBusinessLine]:
        """获取所有业务线"""
        stmt = select(SysBusinessLine).where(SysBusinessLine.status == 1)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_business_line_by_id(self, bl_id: int) -> Optional[SysBusinessLine]:
        """根据ID获取业务线"""
        return await self.session.get(SysBusinessLine, bl_id)

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
        """
        根据参数位置获取映射

        param_location: path/query/body/form/header/file
        """
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
    # 网关管理方法
    # ============================================

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
    # 网关-微服务绑定方法
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
    # LLM 配置管理方法 (v10.0)
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
    # 网关-LLM绑定方法 (v10.0)
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


# ============================================
# RBAC 权限系统数据访问层
# ============================================


class RbacRepository:
    """RBAC权限系统数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================
    # 用户管理
    # ============================================

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

    # ============================================
    # 角色管理
    # ============================================

    async def get_role_by_id(self, role_id: int) -> Optional[SysRole]:
        """根据ID获取角色"""
        return await self.session.get(SysRole, role_id)

    async def get_role_by_code(self, role_code: str) -> Optional[SysRole]:
        """根据角色编码获取角色"""
        stmt = select(SysRole).where(SysRole.role_code == role_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_roles(self) -> List[SysRole]:
        """获取所有角色"""
        stmt = select(SysRole).order_by(SysRole.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_role(self, role: SysRole) -> SysRole:
        """创建角色"""
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update_role(self, role_id: int, **kwargs) -> Optional[SysRole]:
        """更新角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        for key, value in kwargs.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        await self.session.delete(role)
        await self.session.commit()
        return True

    # ============================================
    # 用户角色关联
    # ============================================

    async def get_user_roles(self, user_id: int) -> List[SysRole]:
        """获取用户的所有角色"""
        stmt = (
            select(SysRole)
            .join(SysUserRole, SysRole.id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """给用户分配角色"""
        user_role = SysUserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.commit()
        return True

    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """移除用户角色"""
        stmt = select(SysUserRole).where(
            and_(SysUserRole.user_id == user_id, SysUserRole.role_id == role_id)
        )
        result = await self.session.execute(stmt)
        user_role = result.scalars().first()
        if user_role:
            await self.session.delete(user_role)
            await self.session.commit()
        return True

    async def set_user_roles(self, user_id: int, role_ids: List[int]) -> bool:
        """设置用户角色（覆盖）"""
        # 删除原有角色
        stmt = select(SysUserRole).where(SysUserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        for ur in result.scalars().all():
            await self.session.delete(ur)
        # 添加新角色
        for role_id in role_ids:
            user_role = SysUserRole(user_id=user_id, role_id=role_id)
            self.session.add(user_role)
        await self.session.commit()
        return True

    # ============================================
    # 权限管理
    # ============================================

    async def get_permission_by_id(self, permission_id: int) -> Optional[SysPermission]:
        """根据ID获取权限"""
        return await self.session.get(SysPermission, permission_id)

    async def get_permission_by_code(
        self, permission_code: str
    ) -> Optional[SysPermission]:
        """根据权限编码获取权限"""
        stmt = select(SysPermission).where(
            SysPermission.permission_code == permission_code
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_permissions(self) -> List[SysPermission]:
        """获取所有权限"""
        stmt = select(SysPermission).order_by(
            SysPermission.resource_id, SysPermission.action
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_resource(
        self, resource_id: int
    ) -> List[SysPermission]:
        """获取资源的所有权限"""
        stmt = select(SysPermission).where(SysPermission.resource_id == resource_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_role_permissions(self, role_id: int) -> List[SysPermission]:
        """获取角色的所有权限"""
        stmt = (
            select(SysPermission)
            .join(
                SysRolePermission, SysPermission.id == SysRolePermission.permission_id
            )
            .where(SysRolePermission.role_id == role_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_permissions(self, user_id: int) -> List[SysPermission]:
        """获取用户的所有权限（通过角色）"""
        stmt = (
            select(SysPermission)
            .distinct()
            .join(
                SysRolePermission, SysPermission.id == SysRolePermission.permission_id
            )
            .join(SysUserRole, SysRolePermission.role_id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_permission_to_role(self, role_id: int, permission_id: int) -> bool:
        """给角色分配权限"""
        role_perm = SysRolePermission(role_id=role_id, permission_id=permission_id)
        self.session.add(role_perm)
        await self.session.commit()
        return True

    async def remove_permission_from_role(
        self, role_id: int, permission_id: int
    ) -> bool:
        """移除角色权限"""
        stmt = select(SysRolePermission).where(
            and_(
                SysRolePermission.role_id == role_id,
                SysRolePermission.permission_id == permission_id,
            )
        )
        result = await self.session.execute(stmt)
        role_perm = result.scalars().first()
        if role_perm:
            await self.session.delete(role_perm)
            await self.session.commit()
        return True

    async def set_role_permissions(
        self, role_id: int, permission_ids: List[int]
    ) -> bool:
        """设置角色权限（覆盖）"""
        # 删除原有权限
        stmt = select(SysRolePermission).where(SysRolePermission.role_id == role_id)
        result = await self.session.execute(stmt)
        for rp in result.scalars().all():
            await self.session.delete(rp)
        # 添加新权限
        for perm_id in permission_ids:
            role_perm = SysRolePermission(role_id=role_id, permission_id=perm_id)
            self.session.add(role_perm)
        await self.session.commit()
        return True

    # ============================================
    # 网关权限
    # ============================================

    async def get_gateway_permissions_by_role(
        self, role_id: int
    ) -> List[SysGatewayPermission]:
        """获取角色的网关权限"""
        stmt = select(SysGatewayPermission).where(
            SysGatewayPermission.role_id == role_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gateway_permission(
        self, role_id: int, gateway_id: str
    ) -> Optional[SysGatewayPermission]:
        """获取角色对特定网关的权限"""
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
        # 查找现有权限
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
        """单条网关权限的 upsert：相同跳过、不存在新增、存在但不同则更新"""
        new_vals = {
            "can_create": 1 if perm.get("can_create", False) else 0,
            "can_read": 1 if perm.get("can_read", False) else 0,
            "can_update": 1 if perm.get("can_update", False) else 0,
            "can_delete": 1 if perm.get("can_delete", False) else 0,
            "can_chat": 1 if perm.get("can_chat", False) else 0,
        }
        existing = await self.get_gateway_permission(role_id, perm["gateway_id"])
        if existing:
            # 检查是否有变化
            changed = False
            for k, v in new_vals.items():
                if getattr(existing, k) != v:
                    setattr(existing, k, v)
                    changed = True
            # 相同则跳过，不同则已在上面 setattr 更新
        else:
            # 不存在则新增
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
        # 获取当前所有权限
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

    # ============================================
    # 资源管理
    # ============================================

    async def get_all_resources(self) -> List[SysResource]:
        """获取所有资源"""
        stmt = select(SysResource).order_by(SysResource.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_resource_by_id(self, resource_id: int) -> Optional[SysResource]:
        """根据ID获取资源"""
        return await self.session.get(SysResource, resource_id)

    # ============================================
    # 登录日志
    # ============================================

    async def create_login_log(self, log: SysLoginLog) -> SysLoginLog:
        """创建登录日志"""
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_login_logs(self, limit: int = 100) -> List[SysLoginLog]:
        """获取登录日志"""
        stmt = select(SysLoginLog).order_by(SysLoginLog.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ============================================
    # 业务线管理 (v8.0)
    # ============================================

    async def get_business_line_by_id(self, bl_id: int) -> Optional[SysBusinessLine]:
        """根据ID获取业务线"""
        return await self.session.get(SysBusinessLine, bl_id)

    async def get_business_line_by_code(
        self, line_code: str
    ) -> Optional[SysBusinessLine]:
        """根据编码获取业务线"""
        stmt = select(SysBusinessLine).where(SysBusinessLine.line_code == line_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_business_lines(self) -> List[SysBusinessLine]:
        """获取所有业务线"""
        stmt = select(SysBusinessLine).order_by(SysBusinessLine.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_business_line(self, bl: SysBusinessLine) -> SysBusinessLine:
        """创建业务线"""
        self.session.add(bl)
        await self.session.commit()
        await self.session.refresh(bl)
        return bl

    async def update_business_line(
        self, bl_id: int, **kwargs
    ) -> Optional[SysBusinessLine]:
        """更新业务线"""
        bl = await self.get_business_line_by_id(bl_id)
        if not bl:
            return None
        for key, value in kwargs.items():
            if hasattr(bl, key) and value is not None:
                setattr(bl, key, value)
        await self.session.commit()
        await self.session.refresh(bl)
        return bl

    async def delete_business_line(self, bl_id: int) -> bool:
        """删除业务线"""
        bl = await self.get_business_line_by_id(bl_id)
        if not bl:
            return False
        await self.session.delete(bl)
        await self.session.commit()
        return True

    # ============================================
    # 用户-业务线关联
    # ============================================

    async def get_user_business_lines(self, user_id: int) -> List[SysUserBusinessLine]:
        """获取用户的所有业务线关联"""
        stmt = select(SysUserBusinessLine).where(SysUserBusinessLine.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_managed_business_lines(
        self, user_id: int
    ) -> List[SysUserBusinessLine]:
        """获取用户管理的业务线（is_admin=1）"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_business_line_users(self, bl_id: int) -> List[SysUserBusinessLine]:
        """获取业务线下的所有用户"""
        stmt = select(SysUserBusinessLine).where(
            SysUserBusinessLine.business_line_id == bl_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_user_to_business_line(
        self, user_id: int, bl_id: int, is_admin: bool = False
    ) -> SysUserBusinessLine:
        """添加用户到业务线"""
        ubl = SysUserBusinessLine(
            user_id=user_id, business_line_id=bl_id, is_admin=1 if is_admin else 0
        )
        self.session.add(ubl)
        await self.session.commit()
        await self.session.refresh(ubl)
        return ubl

    async def remove_user_from_business_line(self, user_id: int, bl_id: int) -> bool:
        """从业务线移除用户"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        ubl = result.scalars().first()
        if ubl:
            await self.session.delete(ubl)
            await self.session.commit()
        return True

    async def set_user_business_line_admin(
        self, user_id: int, bl_id: int, is_admin: bool
    ) -> bool:
        """设置用户在业务线的管理员权限"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        ubl = result.scalars().first()
        if ubl:
            ubl.is_admin = 1 if is_admin else 0
            await self.session.commit()
            return True
        return False

    async def is_business_line_admin(self, user_id: int, bl_id: int) -> bool:
        """检查用户是否是某业务线管理员"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
                SysUserBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def is_user_in_business_line(self, user_id: int, bl_id: int) -> bool:
        """检查用户是否属于某业务线"""
        stmt = select(SysUserBusinessLine).where(
            and_(
                SysUserBusinessLine.user_id == user_id,
                SysUserBusinessLine.business_line_id == bl_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    # ============================================
    # 网关权限管理
    # ============================================

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

    async def _upsert_gateway_permission(self, role_id: int, perm: dict) -> None:
        """单条网关权限 upsert"""
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
        """设置角色的网关权限（全量覆盖）"""
        existing_perms = await self.get_gateway_permissions_by_role(role_id)
        existing_map = {p.gateway_id: p for p in existing_perms}
        incoming_ids = {p["gateway_id"] for p in permissions}
        for gw_id, gp in existing_map.items():
            if gw_id not in incoming_ids:
                await self.session.delete(gp)
        for perm in permissions:
            await self._upsert_gateway_permission(role_id, perm)
        await self.session.commit()
        return True

    async def set_role_gateway_permissions_scoped(
        self, role_id: int, permissions: List[dict], scoped_gateway_ids: List[str]
    ) -> bool:
        """按范围设置角色的网关权限"""
        incoming_ids = {p["gateway_id"] for p in permissions}
        for gw_id in scoped_gateway_ids:
            if gw_id not in incoming_ids:
                existing = await self.get_gateway_permission(role_id, gw_id)
                if existing:
                    await self.session.delete(existing)
        for perm in permissions:
            await self._upsert_gateway_permission(role_id, perm)
        await self.session.commit()
        return True

    # ============================================
    # 角色-业务线管理员
    # ============================================

    async def get_role_bl_admin_ids(self, role_id: int) -> List[int]:
        """获取角色作为管理员的业务线ID列表"""
        stmt = select(SysRoleBusinessLine).where(
            and_(
                SysRoleBusinessLine.role_id == role_id,
                SysRoleBusinessLine.is_admin == 1,
            )
        )
        result = await self.session.execute(stmt)
        return [r.business_line_id for r in result.scalars().all()]

    async def set_role_bl_admin_ids(
        self, role_id: int, bl_ids: List[int]
    ) -> bool:
        """设置角色的业务线管理员权限（upsert：相同跳过、不存在新增、多余删除）"""
        stmt = select(SysRoleBusinessLine).where(
            SysRoleBusinessLine.role_id == role_id
        )
        result = await self.session.execute(stmt)
        existing = {r.business_line_id: r for r in result.scalars().all()}
        incoming = set(bl_ids)

        # 删除不在新列表中的记录
        for bl_id, record in existing.items():
            if bl_id not in incoming:
                await self.session.delete(record)

        # 新增不存在的记录
        for bl_id in incoming:
            if bl_id not in existing:
                rbl = SysRoleBusinessLine(
                    role_id=role_id,
                    business_line_id=bl_id,
                    is_admin=1,
                )
                self.session.add(rbl)

        await self.session.commit()
        return True

    async def get_role_bl_admin_ids_for_user(
        self, role_ids: List[int]
    ) -> List[int]:
        """获取一组角色授予管理员权限的所有业务线ID（去重）"""
        if not role_ids:
            return []
        stmt = select(SysRoleBusinessLine.business_line_id).where(
            and_(
                SysRoleBusinessLine.role_id.in_(role_ids),
                SysRoleBusinessLine.is_admin == 1,
            )
        ).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
