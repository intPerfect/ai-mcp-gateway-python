# -*- coding: utf-8 -*-
"""
RBAC Domain Models - 权限管理领域模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class LoginRequest:
    """登录请求"""
    username: str
    password: str


@dataclass
class LoginResponse:
    """登录响应"""
    token: str
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24小时
    user_info: 'UserInfo' = None


@dataclass
class UserInfo:
    """用户信息"""
    id: int
    username: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: int = 1
    roles: List[str] = field(default_factory=list)
    role_ids: List[int] = field(default_factory=list)  # 用户角色ID列表
    permissions: List[str] = field(default_factory=list)
    business_lines: List['BusinessLineInfo'] = field(default_factory=list)  # 用户所属业务线
    managed_business_lines: List['BusinessLineInfo'] = field(default_factory=list)  # 用户管理的业务线
    create_time: Optional[datetime] = None


@dataclass
class UserCreate:
    """创建用户请求"""
    username: str
    password: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_ids: List[int] = field(default_factory=list)
    business_line_ids: List[int] = field(default_factory=list)  # 所属业务线ID列表


@dataclass
class UserUpdate:
    """更新用户请求"""
    real_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[int] = None
    role_ids: Optional[List[int]] = None
    business_line_ids: Optional[List[int]] = None  # 所属业务线ID列表


@dataclass
class RoleInfo:
    """角色信息"""
    id: int
    role_code: str
    role_name: str
    description: Optional[str] = None
    business_line_id: Optional[int] = None  # 所属业务线ID，NULL表示全局角色
    business_line_name: Optional[str] = None  # 业务线名称（前端展示用）
    is_system: int = 0
    status: int = 1
    permissions: List[str] = field(default_factory=list)
    permission_ids: List[int] = field(default_factory=list)
    data_permissions: Optional['DataPermissionSet'] = None
    create_time: Optional[datetime] = None


@dataclass
class RoleCreate:
    """创建角色请求"""
    role_code: str
    role_name: str
    description: Optional[str] = None
    business_line_id: Optional[int] = None  # 所属业务线ID，业务线管理员创建时自动填充
    permission_ids: List[int] = field(default_factory=list)


@dataclass
class RoleUpdate:
    """更新角色请求"""
    role_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    permission_ids: Optional[List[int]] = None


@dataclass
class PermissionInfo:
    """权限信息"""
    id: int
    permission_code: str
    permission_name: str
    resource_id: int
    action: str
    resource_name: Optional[str] = None
    description: Optional[str] = None
    status: int = 1


@dataclass
class ResourceInfo:
    """资源信息"""
    id: int
    resource_code: str
    resource_name: str
    resource_type: str = 'menu'
    parent_id: int = 0
    api_path: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    status: int = 1
    children: List['ResourceInfo'] = field(default_factory=list)


@dataclass
class BusinessLineInfo:
    """业务线信息"""
    id: int
    line_code: str
    line_name: str
    description: Optional[str] = None
    status: int = 1
    is_admin: bool = False  # 当前用户是否是该业务线管理员
    create_time: Optional[datetime] = None


@dataclass
class UserBusinessLine:
    """用户-业务线关联"""
    user_id: int
    business_line_id: int
    is_admin: bool = False
    business_line: Optional[BusinessLineInfo] = None


@dataclass
class DataScope:
    """数据权限范围"""
    business_lines: List[str] = field(default_factory=list)
    gateway_ids: List[str] = field(default_factory=list)
    
    def has_business_line(self, business_line: str) -> bool:
        """检查是否有业务线权限"""
        if not self.business_lines:  # 空列表表示全部权限
            return True
        return business_line in self.business_lines
    
    def has_gateway(self, gateway_id: str) -> bool:
        """检查是否有网关权限"""
        if not self.gateway_ids:  # 空列表表示全部权限
            return True
        return gateway_id in self.gateway_ids


@dataclass
class TokenPayload:
    """JWT Token载荷"""
    sub: str  # user_id
    username: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    data_scope: Optional[DataScope] = None
    managed_business_line_ids: List[int] = field(default_factory=list)  # 用户管理的业务线ID列表
    exp: Optional[int] = None
    iat: Optional[int] = None


@dataclass
class DataPermissionCreate:
    """创建数据权限请求"""
    role_id: int
    business_line: Optional[str] = None
    gateway_id: Optional[str] = None
    permission_id: int = None


@dataclass
class DataPermissionSet:
    """数据权限配置集合"""
    business_lines: List[str] = field(default_factory=list)
    gateway_ids: List[str] = field(default_factory=list)
    microservice_ids: List[int] = field(default_factory=list)
    chat_access: bool = True  # 是否有对话权限


@dataclass
class PermissionTreeNode:
    """权限树节点"""
    id: int
    code: str
    name: str
    resource_id: int
    resource_name: str
    action: str
    checked: bool = False


@dataclass
class ResourcePermissionGroup:
    """资源权限分组（用于权限树展示）"""
    resource_id: int
    resource_code: str
    resource_name: str
    permissions: List['PermissionTreeNode'] = field(default_factory=list)


@dataclass
class DataScopeTreeNode:
    """数据权限树节点"""
    id: str
    name: str
    type: str  # 'business_line' | 'microservice' | 'gateway'
    parent_id: Optional[str] = None
    children: List['DataScopeTreeNode'] = field(default_factory=list)
    checked: bool = False


@dataclass
class GatewayPermission:
    """网关权限配置"""
    gateway_id: str
    gateway_name: Optional[str] = None
    can_create: bool = False
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_chat: bool = False


@dataclass
class GatewayPermissionSet:
    """角色的网关权限集合"""
    permissions: List[GatewayPermission] = field(default_factory=list)