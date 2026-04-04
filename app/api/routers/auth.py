# -*- coding: utf-8 -*-
"""
Auth Router - 认证相关API路由
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_db_session
from app.domain.rbac import RbacService, LoginRequest, LoginResponse, UserInfo
from app.utils.result import Result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


def _get_rbac_service(session: AsyncSession = Depends(get_db_session)) -> RbacService:
    """创建 RbacService 实例（供本模块内部 Depends 使用）"""
    return RbacService(session)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    rbac_service: RbacService = Depends(_get_rbac_service),
) -> Optional[UserInfo]:
    """从请求头中提取并验证 Bearer Token，返回当前登录用户信息。

    未携带 Token 或 Token 无效时返回 None（不抛异常）。

    Returns:
        已认证用户的 UserInfo，或 None。
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    token_payload = await rbac_service.validate_token(token)
    if not token_payload:
        return None
    
    user_id = int(token_payload.sub)
    return await rbac_service.get_user_info(user_id)


async def require_auth(
    current_user: Optional[UserInfo] = Depends(get_current_user)
) -> UserInfo:
    """要求用户已认证且未被禁用，否则抛出 HTTP 401/403。

    Raises:
        HTTPException(401): 未登录或 Token 已过期。
        HTTPException(403): 用户已被禁用。
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录或Token已过期")
    if current_user.status != 1:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    return current_user


def require_permission(permission_code: str):
    """生成权限校验依赖：要求当前用户拥有指定权限码。

    SUPER_ADMIN 角色自动放行。

    Args:
        permission_code: 所需权限码，例如 ``"role:read"``。

    Returns:
        一个可用于 ``Depends(...)`` 的异步函数。
    """
    async def check_permission(
        current_user: UserInfo = Depends(require_auth)
    ) -> UserInfo:
        if "SUPER_ADMIN" in current_user.roles:
            return current_user
        if permission_code not in current_user.permissions:
            raise HTTPException(
                status_code=403, 
                detail=f"缺少权限: {permission_code}"
            )
        return current_user
    return check_permission


@router.post("/login", response_model=Result[LoginResponse])
async def login(
    request: LoginRequest,
    rbac_service: RbacService = Depends(_get_rbac_service),
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP"),
):
    """
    用户登录
    
    Returns:
        LoginResponse: 登录响应，包含Token和用户信息
    """
    # 获取客户端IP
    client_ip = x_forwarded_for or x_real_ip or "unknown"
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    try:
        result = await rbac_service.login(request, client_ip)
        return Result.success(data=result, message="登录成功")
    except Exception as e:
        logger.warning(f"Login failed for user {request.username}: {e}")
        return Result.fail(code="4001", message=str(e))


@router.post("/logout", response_model=Result)
async def logout(
    current_user: UserInfo = Depends(require_auth)
):
    """
    用户登出
    
    Note: JWT无状态，服务端不维护session，登出只需客户端删除Token
    """
    logger.info(f"User {current_user.username} logged out")
    return Result.success(message="登出成功")


@router.get("/userinfo", response_model=Result[UserInfo])
async def get_userinfo(
    current_user: UserInfo = Depends(require_auth)
):
    """
    获取当前用户信息
    """
    return Result.success(data=current_user)


@router.get("/check", response_model=Result)
async def check_auth(
    current_user: Optional[UserInfo] = Depends(get_current_user)
):
    """
    检查登录状态
    """
    if current_user:
        return Result.success(
            data={"logged_in": True, "username": current_user.username},
            message="已登录"
        )
    return Result.fail(code="4001", message="未登录")