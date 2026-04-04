# -*- coding: utf-8 -*-
"""
Database Repository - 兼容导入层
保持原有 McpGatewayRepository 和 RbacRepository 接口不变，
内部委托给拆分后的领域仓库。

新代码建议直接使用 app.infrastructure.database.repositories 中的领域仓库。
"""

from typing import List, Optional
from sqlalchemy import select

from app.infrastructure.database.models import SysBusinessLine

# 导入所有领域仓库
from app.infrastructure.database.repositories.gateway_repo import GatewayRepository
from app.infrastructure.database.repositories.auth_repo import AuthRepository
from app.infrastructure.database.repositories.tool_repo import ToolRepository
from app.infrastructure.database.repositories.microservice_repo import MicroserviceRepository
from app.infrastructure.database.repositories.llm_config_repo import LlmConfigRepository
from app.infrastructure.database.repositories.user_repo import UserRepository
from app.infrastructure.database.repositories.role_repo import RoleRepository
from app.infrastructure.database.repositories.permission_repo import PermissionRepository
from app.infrastructure.database.repositories.business_line_repo import BusinessLineRepository
from app.infrastructure.database.repositories.gateway_permission_repo import GatewayPermissionRepository


class McpGatewayRepository(
    GatewayRepository,
    AuthRepository,
    ToolRepository,
    MicroserviceRepository,
    LlmConfigRepository,
):
    """MCP网关数据访问层（兼容层）

    组合了网关、认证、工具、微服务、LLM配置等领域仓库。
    新代码建议直接使用对应的领域仓库类。
    """

    # McpGatewayRepository 原有的业务线方法（带 status==1 过滤）
    # 与 RbacRepository/BusinessLineRepository 的实现不同，需保留
    async def get_all_business_lines(self) -> List[SysBusinessLine]:
        """获取所有业务线（仅状态为1的）"""
        stmt = select(SysBusinessLine).where(SysBusinessLine.status == 1)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_business_line_by_id(self, bl_id: int) -> Optional[SysBusinessLine]:
        """根据ID获取业务线"""
        return await self.session.get(SysBusinessLine, bl_id)


class RbacRepository(
    UserRepository,
    RoleRepository,
    PermissionRepository,
    BusinessLineRepository,
    GatewayPermissionRepository,
):
    """RBAC权限系统数据访问层（兼容层）

    组合了用户、角色、权限、业务线、网关权限等领域仓库。
    新代码建议直接使用对应的领域仓库类。
    """
    pass
