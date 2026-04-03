# -*- coding: utf-8 -*-
"""
RBAC Domain - 权限管理领域模块
"""
from app.domain.rbac.models import (
    LoginRequest,
    LoginResponse,
    UserInfo,
    UserCreate,
    UserUpdate,
    RoleInfo,
    RoleCreate,
    RoleUpdate,
    PermissionInfo,
    ResourceInfo,
    BusinessLineInfo,
    UserBusinessLine,
    DataScope,
    TokenPayload,
    DataPermissionSet,
    PermissionTreeNode,
    ResourcePermissionGroup,
    DataScopeTreeNode,
    GatewayPermission,
    GatewayPermissionSet
)
from app.domain.rbac.service import RbacService, PermissionService

__all__ = [
    # Models
    "LoginRequest",
    "LoginResponse",
    "UserInfo",
    "UserCreate",
    "UserUpdate",
    "RoleInfo",
    "RoleCreate",
    "RoleUpdate",
    "PermissionInfo",
    "ResourceInfo",
    "BusinessLineInfo",
    "UserBusinessLine",
    "DataScope",
    "TokenPayload",
    "DataPermissionSet",
    "PermissionTreeNode",
    "ResourcePermissionGroup",
    "DataScopeTreeNode",
    "GatewayPermission",
    "GatewayPermissionSet",
    # Services
    "RbacService",
    "PermissionService"
]