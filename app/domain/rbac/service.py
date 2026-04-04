# -*- coding: utf-8 -*-
"""
RBAC Service - 权限管理服务层
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List
from jose import jwt, JWTError
import bcrypt

from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import (
    UserRepository, RoleRepository, PermissionRepository,
    BusinessLineRepository, GatewayPermissionRepository,
)
from app.infrastructure.database.models import (
    SysUser, SysRole,
    SysPermission, SysLoginLog
)
from app.domain.rbac.models import (
    LoginRequest, LoginResponse, UserInfo,
    DataScope, TokenPayload, BusinessLineInfo
)
from app.utils.exceptions import AuthException
from app.infrastructure.cache.redis_client import get_redis, PermissionCache
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# JWT配置（从配置中心读取）
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_HOURS = settings.jwt_expire_hours


class RbacService:
    """RBAC权限管理服务"""
    
    def __init__(self, session: AsyncSession):
        """初始化 RBAC 服务，创建所需的 Repository 实例。"""
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)
        self.business_line_repo = BusinessLineRepository(session)
        self.gateway_permission_repo = GatewayPermissionRepository(session)
    
    async def login(self, request: LoginRequest, client_ip: str) -> LoginResponse:
        """
        用户登录
        
        Args:
            request: 登录请求
            client_ip: 客户端IP
            
        Returns:
            LoginResponse: 登录响应
            
        Raises:
            AuthException: 登录失败
        """
        # 查找用户
        user = await self.user_repo.get_user_by_username(request.username)
        
        # 记录登录日志
        log = SysLoginLog(
            user_id=user.id if user else None,
            username=request.username,
            login_ip=client_ip,
            login_status=0
        )
        
        if not user:
            log.fail_reason = "用户不存在"
            await self.permission_repo.create_login_log(log)
            raise AuthException("用户名或密码错误")
        
        if user.status != 1:
            log.fail_reason = "用户已禁用"
            await self.permission_repo.create_login_log(log)
            raise AuthException("用户已被禁用")
        
        # 验证密码
        if not bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            log.fail_reason = "密码错误"
            await self.permission_repo.create_login_log(log)
            raise AuthException("用户名或密码错误")
        
        # 更新登录信息
        await self.user_repo.update_user_login_info(user.id, client_ip)
        
        # 记录成功日志
        log.user_id = user.id
        log.login_status = 1
        await self.permission_repo.create_login_log(log)
        
        # 获取用户角色和权限
        roles = await self.role_repo.get_user_roles(user.id)
        permissions = await self.permission_repo.get_user_permissions(user.id)
        
        # 获取数据权限
        data_scope = await self._build_data_scope(user.id)
        
        # 获取用户管理的业务线ID列表
        managed_bl_ids = await self._get_managed_business_line_ids(user.id)
        
        # 生成Token
        token = self._create_access_token(
            user_id=user.id,
            username=user.username,
            roles=[r.role_code for r in roles],
            permissions=[p.permission_code for p in permissions],
            data_scope=data_scope,
            managed_business_line_ids=managed_bl_ids
        )
        
        # 构建用户信息
        user_info = await self._build_user_info(user, roles, permissions)
        
        logger.info(f"User {user.username} logged in successfully from {client_ip}")
        
        return LoginResponse(
            token=token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            user_info=user_info
        )
    
    async def _get_perm_cache(self) -> Optional[PermissionCache]:
        """获取权限缓存实例，Redis不可用时返回None"""
        try:
            redis = await get_redis()
            return PermissionCache(redis)
        except Exception:
            return None

    async def get_user_info(self, user_id: int) -> Optional[UserInfo]:
        """获取用户信息（Cache Aside）"""
        # 1. 查缓存
        cache = await self._get_perm_cache()
        if cache:
            cached = await cache.get_user_info(user_id)
            if cached:
                return UserInfo(**cached)

        # 2. 缓存未命中，查DB
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return None

        roles = await self.role_repo.get_user_roles(user_id)
        permissions = await self.permission_repo.get_user_permissions(user_id)
        user_info = await self._build_user_info(user, roles, permissions)

        # 3. 写入缓存
        if cache:
            from dataclasses import asdict
            await cache.set_user_info(user_id, asdict(user_info))

        return user_info
    
    async def validate_token(self, token: str) -> Optional[TokenPayload]:
        """
        验证JWT Token
        
        Args:
            token: JWT Token
            
        Returns:
            TokenPayload: Token载荷，验证失败返回None
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            data_scope = None
            if "data_scope" in payload:
                ds = payload["data_scope"]
                data_scope = DataScope(
                    business_lines=ds.get("business_lines", []),
                    gateway_ids=ds.get("gateway_ids", [])
                )
            
            managed_business_line_ids = payload.get("managed_business_line_ids", [])
            
            return TokenPayload(
                sub=user_id,
                username=payload.get("username", ""),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                data_scope=data_scope,
                managed_business_line_ids=managed_business_line_ids,
                exp=payload.get("exp"),
                iat=payload.get("iat")
            )
        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    def _create_access_token(
        self,
        user_id: int,
        username: str,
        roles: List[str],
        permissions: List[str],
        data_scope: Optional[DataScope] = None,
        managed_business_line_ids: List[int] = None
    ) -> str:
        """创建JWT Token"""
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        payload = {
            "sub": str(user_id),
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "exp": expire,
            "iat": int(time.time())
        }
        
        if data_scope:
            payload["data_scope"] = {
                "business_lines": data_scope.business_lines,
                "gateway_ids": data_scope.gateway_ids
            }
        
        
        if managed_business_line_ids:
            payload["managed_business_line_ids"] = managed_business_line_ids
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    async def _build_user_info(
        self,
        user: SysUser,
        roles: List[SysRole],
        permissions: List[SysPermission]
    ) -> UserInfo:
        """构建用户信息"""
        # 获取用户所属业务线
        business_lines = await self._get_user_business_lines(user.id)
        # 获取用户管理的业务线
        managed_business_lines = await self._get_user_managed_business_lines(user.id)
    
        return UserInfo(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            email=user.email,
            phone=user.phone,
            avatar=user.avatar,
            status=user.status,
            roles=[r.role_code for r in roles],
            role_ids=[r.id for r in roles],
            permissions=[p.permission_code for p in permissions],
            business_lines=business_lines,
            managed_business_lines=managed_business_lines,
            create_time=user.create_time
        )
    
    async def _get_user_business_lines(self, user_id: int) -> List[BusinessLineInfo]:
        """获取用户所属业务线列表"""
        ubls = await self.business_line_repo.get_user_business_lines(user_id)
        result = []
        for ubl in ubls:
            bl = await self.business_line_repo.get_business_line_by_id(ubl.business_line_id)
            if bl:
                result.append(BusinessLineInfo(
                    id=bl.id,
                    line_code=bl.line_code,
                    line_name=bl.line_name,
                    description=bl.description,
                    status=bl.status,
                    is_admin=bool(ubl.is_admin),
                    create_time=bl.create_time
                ))
        return result
    
    async def _get_user_managed_business_lines(self, user_id: int) -> List[BusinessLineInfo]:
        """获取用户管理的业务线列表（包含用户级别 + 角色级别的管理员权限）"""
        # 用户级别的管理员业务线
        ubls = await self.business_line_repo.get_user_managed_business_lines(user_id)
        managed_bl_ids = set(ubl.business_line_id for ubl in ubls)

        # 角色级别的管理员业务线
        roles = await self.role_repo.get_user_roles(user_id)
        role_ids = [r.id for r in roles]
        role_bl_admin_ids = await self.business_line_repo.get_role_bl_admin_ids_for_user(role_ids)
        managed_bl_ids.update(role_bl_admin_ids)

        result = []
        for bl_id in managed_bl_ids:
            bl = await self.business_line_repo.get_business_line_by_id(bl_id)
            if bl:
                result.append(BusinessLineInfo(
                    id=bl.id,
                    line_code=bl.line_code,
                    line_name=bl.line_name,
                    description=bl.description,
                    status=bl.status,
                    is_admin=True,
                    create_time=bl.create_time
                ))
        return result
    
    async def _get_managed_business_line_ids(self, user_id: int) -> List[int]:
        """获取用户管理的业务线ID列表"""
        ubls = await self.business_line_repo.get_user_managed_business_lines(user_id)
        return [ubl.business_line_id for ubl in ubls]
    
    async def is_business_line_admin(self, user_id: int, bl_id: int) -> bool:
        """检查用户是否是某业务线管理员"""
        # 超级管理员拥有所有权限
        roles = await self.role_repo.get_user_roles(user_id)
        for role in roles:
            if role.role_code == "SUPER_ADMIN":
                return True
        return await self.business_line_repo.is_business_line_admin(user_id, bl_id)
    
    async def get_user_managed_business_line_ids(self, user_id: int) -> List[int]:
        """获取用户管理的业务线ID列表（对外接口）"""
        # 超级管理员返回空列表（表示全部权限）
        roles = await self.role_repo.get_user_roles(user_id)
        for role in roles:
            if role.role_code == "SUPER_ADMIN":
                return []  # 空列表表示全部
        return await self._get_managed_business_line_ids(user_id)
    
    async def _build_data_scope(self, user_id: int) -> Optional[DataScope]:
        """构建数据权限范围 - 基于网关权限"""
        # 获取用户所有角色
        roles = await self.role_repo.get_user_roles(user_id)
        
        gateway_ids = set()
        has_all_permission = False
        
        for role in roles:
            # 检查是否是超级管理员
            if role.role_code == "SUPER_ADMIN":
                has_all_permission = True
                break
            
            # 获取角色的网关权限
            gateway_perms = await self.gateway_permission_repo.get_gateway_permissions_by_role(role.id)
            for gp in gateway_perms:
                if gp.can_read and gp.gateway_id:
                    gateway_ids.add(gp.gateway_id)
        
        if has_all_permission:
            return DataScope(business_lines=[], gateway_ids=[])  # 空列表表示全部权限
        
        return DataScope(
            business_lines=[],  # 新权限模型不再基于业务线
            gateway_ids=list(gateway_ids)
        )


class PermissionService:
    """权限校验服务"""
    
    def __init__(self, session: AsyncSession):
        self.permission_repo = PermissionRepository(session)
        self.role_repo = RoleRepository(session)
        self.gateway_permission_repo = GatewayPermissionRepository(session)

    async def _get_perm_cache(self) -> Optional[PermissionCache]:
        try:
            redis = await get_redis()
            return PermissionCache(redis)
        except Exception:
            return None
    
    async def check_permission(
        self,
        user_id: int,
        permission_code: str,
        gateway_id: Optional[str] = None,
        permission_type: str = "read"
    ) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_id: 用户ID
            permission_code: 权限编码
            gateway_id: 网关ID(可选，用于网关权限检查)
            permission_type: 网关权限类型 (read/create/update/delete/chat)
            
        Returns:
            bool: 是否有权限
        """
        # 获取用户权限
        permissions = await self.permission_repo.get_user_permissions(user_id)
        permission_codes = [p.permission_code for p in permissions]
        
        # 检查功能权限
        if permission_code not in permission_codes:
            return False
        
        # 获取用户角色检查数据权限
        roles = await self.role_repo.get_user_roles(user_id)
        role_codes = [r.role_code for r in roles]
        
        # 超级管理员拥有全部权限
        if "SUPER_ADMIN" in role_codes:
            return True
        
        # 如果指定了网关，需要检查网关权限
        if gateway_id:
            return await self._check_data_permission(
                user_id, 
                gateway_id=gateway_id,
                permission_type=permission_type
            )
        
        return True
    
    async def _check_data_permission(
        self,
        user_id: int,
        gateway_id: Optional[str] = None,
        permission_type: str = "read"
    ) -> bool:
        """检查网关权限
        
        Args:
            user_id: 用户ID
            gateway_id: 网关ID
            permission_type: 权限类型 (read/create/update/delete/chat)
        """
        if not gateway_id:
            return True
        
        roles = await self.role_repo.get_user_roles(user_id)
        
        for role in roles:
            gateway_perms = await self.gateway_permission_repo.get_gateway_permissions_by_role(role.id)
            
            for gp in gateway_perms:
                if gp.gateway_id == gateway_id:
                    # 检查对应权限类型
                    perm_attr = f"can_{permission_type}"
                    if getattr(gp, perm_attr, False):
                        return True
        
        return False
    
    async def get_accessible_gateways(self, user_id: int) -> List[str]:
        """获取用户可访问的网关ID列表（Cache Aside）"""
        roles = await self.role_repo.get_user_roles(user_id)
        
        # 超级管理员可访问全部
        for role in roles:
            if role.role_code == "SUPER_ADMIN":
                return []  # 空列表表示全部
        
        # 1. 查缓存
        cache = await self._get_perm_cache()
        if cache:
            cached = await cache.get_accessible_gateways(user_id)
            if cached is not None:
                return cached
        
        # 2. 缓存未命中，查DB
        gateway_ids = set()
        for role in roles:
            gateway_perms = await self.gateway_permission_repo.get_gateway_permissions_by_role(role.id)
            for gp in gateway_perms:
                if gp.can_read and gp.gateway_id:
                    gateway_ids.add(gp.gateway_id)
        
        result = list(gateway_ids)
        
        # 3. 写入缓存
        if cache:
            await cache.set_accessible_gateways(user_id, result)
        
        return result
    
    async def check_gateway_permission(
        self, 
        user_id: int, 
        gateway_id: str, 
        permission_type: str = "read"
    ) -> bool:
        """检查用户对特定网关的权限（Cache Aside）"""
        roles = await self.role_repo.get_user_roles(user_id)
        
        # 超级管理员有全部权限
        for role in roles:
            if role.role_code == "SUPER_ADMIN":
                return True
        
        cache = await self._get_perm_cache()
        
        for role in roles:
            # 尝试从缓存获取角色网关权限
            perms_data = None
            if cache:
                perms_data = await cache.get_gateway_perms_by_role(role.id)
            
            if perms_data is not None:
                for gp in perms_data:
                    if gp.get("gateway_id") == gateway_id:
                        if gp.get(f"can_{permission_type}", False):
                            return True
            else:
                gateway_perms = await self.gateway_permission_repo.get_gateway_permissions_by_role(role.id)
                # 写入缓存
                if cache and gateway_perms:
                    perms_list = [
                        {"gateway_id": gp.gateway_id, "can_create": gp.can_create,
                         "can_read": gp.can_read, "can_update": gp.can_update,
                         "can_delete": gp.can_delete, "can_chat": gp.can_chat}
                        for gp in gateway_perms
                    ]
                    await cache.set_gateway_perms_by_role(role.id, perms_list)
                
                for gp in gateway_perms:
                    if gp.gateway_id == gateway_id:
                        perm_attr = f"can_{permission_type}"
                        if getattr(gp, perm_attr, False):
                            return True
        
        return False