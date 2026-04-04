# -*- coding: utf-8 -*-
"""
Dependency Providers - FastAPI 依赖注入统一提供器

通过 FastAPI 原生 Depends 机制，为 Router 层提供 Repository / Service 实例，
消除各端点手动 new Repository 的样板代码。

用法示例::

    from app.api.deps import CurrentUser, GatewayRepo, PermissionSvc

    @router.get("/gateways")
    async def list_gateways(
        current_user: CurrentUser,
        gateway_repo: GatewayRepo,
        permission_svc: PermissionSvc,
    ):
        ...
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories import (
    AuthRepository,
    BusinessLineRepository,
    GatewayPermissionRepository,
    GatewayRepository,
    LlmConfigRepository,
    MicroserviceRepository,
    PermissionRepository,
    RoleRepository,
    ToolRepository,
    UserRepository,
)
from app.api.routers.auth import require_auth, require_permission, UserInfo  # noqa: F401 - re-export

# ============================================================
# Type alias: 当前登录用户
# ============================================================

CurrentUser = Annotated[UserInfo, Depends(require_auth)]

# ============================================================
# Database Session
# ============================================================

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# ============================================================
# Repository Depends factories
# ============================================================


def _get_auth_repository(session: AsyncSession = Depends(get_db_session)) -> AuthRepository:
    return AuthRepository(session)


def _get_business_line_repository(session: AsyncSession = Depends(get_db_session)) -> BusinessLineRepository:
    return BusinessLineRepository(session)


def _get_gateway_permission_repository(session: AsyncSession = Depends(get_db_session)) -> GatewayPermissionRepository:
    return GatewayPermissionRepository(session)


def _get_gateway_repository(session: AsyncSession = Depends(get_db_session)) -> GatewayRepository:
    return GatewayRepository(session)


def _get_llm_config_repository(session: AsyncSession = Depends(get_db_session)) -> LlmConfigRepository:
    return LlmConfigRepository(session)


def _get_microservice_repository(session: AsyncSession = Depends(get_db_session)) -> MicroserviceRepository:
    return MicroserviceRepository(session)


def _get_permission_repository(session: AsyncSession = Depends(get_db_session)) -> PermissionRepository:
    return PermissionRepository(session)


def _get_role_repository(session: AsyncSession = Depends(get_db_session)) -> RoleRepository:
    return RoleRepository(session)


def _get_tool_repository(session: AsyncSession = Depends(get_db_session)) -> ToolRepository:
    return ToolRepository(session)


def _get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)


# Annotated 类型别名 —— Router 函数签名中直接使用
AuthRepo = Annotated[AuthRepository, Depends(_get_auth_repository)]
BusinessLineRepo = Annotated[BusinessLineRepository, Depends(_get_business_line_repository)]
GatewayPermissionRepo = Annotated[GatewayPermissionRepository, Depends(_get_gateway_permission_repository)]
GatewayRepo = Annotated[GatewayRepository, Depends(_get_gateway_repository)]
LlmConfigRepo = Annotated[LlmConfigRepository, Depends(_get_llm_config_repository)]
MicroserviceRepo = Annotated[MicroserviceRepository, Depends(_get_microservice_repository)]
PermissionRepo = Annotated[PermissionRepository, Depends(_get_permission_repository)]
RoleRepo = Annotated[RoleRepository, Depends(_get_role_repository)]
ToolRepo = Annotated[ToolRepository, Depends(_get_tool_repository)]
UserRepo = Annotated[UserRepository, Depends(_get_user_repository)]

# ============================================================
# Service Depends factories
# ============================================================

# 延迟导入避免循环依赖
def _get_rbac_service(session: AsyncSession = Depends(get_db_session)):
    from app.domain.rbac.service import RbacService
    return RbacService(session)


def _get_permission_service(session: AsyncSession = Depends(get_db_session)):
    from app.domain.rbac.service import PermissionService
    return PermissionService(session)


from app.domain.rbac.service import RbacService, PermissionService  # noqa: E402

RbacSvc = Annotated[RbacService, Depends(_get_rbac_service)]
PermissionSvc = Annotated[PermissionService, Depends(_get_permission_service)]

# ============================================================
# 常用工具函数（多个 Router 共用）
# ============================================================


def is_super_admin(current_user: UserInfo) -> bool:
    """检查用户是否拥有 SUPER_ADMIN 角色。"""
    return "SUPER_ADMIN" in current_user.roles


async def get_user_managed_business_line_ids(
    repo: BusinessLineRepository, user_id: int
) -> list[int]:
    """获取用户管理的业务线ID列表。"""
    managed = await repo.get_user_managed_business_lines(user_id)
    return [ubl.business_line_id for ubl in managed]


__all__ = [
    # Type aliases
    "UserInfo", "CurrentUser", "DbSession",
    # Repository aliases
    "AuthRepo", "BusinessLineRepo", "GatewayPermissionRepo",
    "GatewayRepo", "LlmConfigRepo", "MicroserviceRepo",
    "PermissionRepo", "RoleRepo", "ToolRepo", "UserRepo",
    # Service aliases
    "RbacSvc", "PermissionSvc",
    # Utilities
    "is_super_admin", "get_user_managed_business_line_ids",
]
