# -*- coding: utf-8 -*-
"""
Tools Router - 工具管理路由
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.services.mcp_tool_registry import mcp_tool_registry
from app.utils.result import Result
from app.api.routers.auth import (
    require_permission,
    UserInfo as CurrentUser,
)
from app.domain.rbac.service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tools")
async def list_tools(
    gateway_id: str = None,
    current_user: CurrentUser = Depends(require_permission("tool:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取所有已注册的工具（按网关权限过滤）"""
    try:
        from app.infrastructure.database.repositories import ToolRepository

        repository = ToolRepository(db)

        # 超级管理员可查看所有
        if "SUPER_ADMIN" in current_user.roles:
            if gateway_id:
                tools = await repository.get_tools_by_gateway_id(gateway_id)
            else:
                tools = await repository.get_tools_by_gateway_id()
        else:
            # 获取用户可访问的网关
            rbac_service = PermissionService(db)
            accessible_ids = await rbac_service.get_accessible_gateways(current_user.id)

            if gateway_id:
                # 检查是否有该网关的权限
                if gateway_id not in accessible_ids:
                    return Result.error("FORBIDDEN", "无权限访问此网关")
                tools = await repository.get_tools_by_gateway_id(gateway_id)
            else:
                # 获取所有可访问网关的工具
                all_tools = await repository.get_tools_by_gateway_id()
                tools = [t for t in all_tools if t.gateway_id in accessible_ids]

        data = [
            {
                "id": t.id,
                "gateway_id": t.gateway_id,
                "tool_id": t.tool_id,
                "tool_name": t.tool_name,
                "tool_type": t.tool_type,
                "tool_description": t.tool_description,
                "tool_version": t.tool_version,
                "enabled": t.enabled,
                "call_status": t.call_status,
                "call_count": t.call_count,
                "error_count": t.error_count,
                "last_call_code": t.last_call_code,
                "last_call_time": str(t.last_call_time) if t.last_call_time else None,
            }
            for t in tools
        ]
        return Result.success({"tools": data, "total": len(data)})
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.get("/tools/status")
async def get_tools_status(
    gateway_id: str = None,
    current_user: CurrentUser = Depends(require_permission("tool:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取工具状态（按网关权限过滤）"""
    try:
        from app.infrastructure.database.repositories import ToolRepository

        repository = ToolRepository(db)

        # 超级管理员可查看所有
        if "SUPER_ADMIN" in current_user.roles:
            if gateway_id:
                tools = await repository.get_tools_by_gateway_id(gateway_id)
            else:
                tools = await repository.get_tools_by_gateway_id()
        else:
            rbac_service = PermissionService(db)
            accessible_ids = await rbac_service.get_accessible_gateways(current_user.id)

            if gateway_id and gateway_id not in accessible_ids:
                return Result.error("FORBIDDEN", "无权限访问此网关")

            all_tools = await repository.get_tools_by_gateway_id()
            if gateway_id:
                tools = [t for t in all_tools if t.gateway_id == gateway_id]
            else:
                tools = [t for t in all_tools if t.gateway_id in accessible_ids]

        statuses = mcp_tool_registry.get_tool_statuses()
        status_map = {s.name: s for s in statuses}

        data = [
            {
                "gateway_id": t.gateway_id,
                "tool_name": t.tool_name,
                "call_status": t.call_status,
                "call_count": t.call_count,
                "error_count": t.error_count,
                "registry_status": status_map.get(t.tool_name, None),
            }
            for t in tools
        ]
        return Result.success({"tools": data, "total": len(data)})
    except Exception as e:
        logger.error(f"获取工具状态失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/tools/reload")
async def reload_tools(
    gateway_id: str = None,
    force: bool = False,
    current_user: CurrentUser = Depends(require_permission("tool:update")),
    db: AsyncSession = Depends(get_db_session),
):
    """重新加载工具（检查网关权限）"""
    try:
        # 如果指定了gateway_id，检查权限
        if gateway_id and "SUPER_ADMIN" not in current_user.roles:
            rbac_service = PermissionService(db)
            has_perm = await rbac_service.check_gateway_permission(
                current_user.id, gateway_id, "update"
            )
            if not has_perm:
                return Result.error("FORBIDDEN", "无权限操作此网关")

        result = await mcp_tool_registry.load_tools_from_db(
            db, gateway_id, force_reload=force
        )
        return Result.success(result)
    except Exception as e:
        logger.error(f"重新加载工具失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.get("/tools/{tool_name}/status")
async def get_tool_status(
    tool_name: str,
    gateway_id: str = "gateway_001",
    current_user: CurrentUser = Depends(require_permission("tool:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个工具的详细状态"""
    try:
        # 检查网关权限
        if "SUPER_ADMIN" not in current_user.roles:
            rbac_service = PermissionService(db)
            has_perm = await rbac_service.check_gateway_permission(
                current_user.id, gateway_id, "read"
            )
            if not has_perm:
                return Result.error("FORBIDDEN", "无权限访问此网关")

        from app.infrastructure.database.repositories import ToolRepository

        repository = ToolRepository(db)

        tool = await repository.get_tool_by_name(gateway_id, tool_name)
        if not tool:
            return Result.not_found(f"工具不存在: {tool_name}")

        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        status = statuses.get(tool_name)

        return Result.success(
            {
                "id": tool.id,
                "gateway_id": tool.gateway_id,
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "enabled": tool.enabled,
                "call_status": tool.call_status,
                "call_count": tool.call_count,
                "error_count": tool.error_count,
                "last_call_code": tool.last_call_code,
                "last_call_time": str(tool.last_call_time)
                if tool.last_call_time
                else None,
                "registry_status": status.status if status else "unknown",
                "registry_http_url": status.http_url if status else "",
                "registry_error": status.error if status else None,
            }
        )
    except Exception as e:
        logger.error(f"获取工具状态失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/tools/{tool_name}/health-check")
async def health_check_tool(
    tool_name: str,
    gateway_id: str = "gateway_001",
    current_user: CurrentUser = Depends(require_permission("tool:read")),
    db: AsyncSession = Depends(get_db_session),
):
    """对指定工具进行健康检查"""
    try:
        # 检查网关权限
        if "SUPER_ADMIN" not in current_user.roles:
            rbac_service = PermissionService(db)
            has_perm = await rbac_service.check_gateway_permission(
                current_user.id, gateway_id, "read"
            )
            if not has_perm:
                return Result.error("FORBIDDEN", "无权限访问此网关")

        from app.infrastructure.database.repositories import ToolRepository

        repository = ToolRepository(db)
        tool = await repository.get_tool_by_name(gateway_id, tool_name)

        if not tool:
            return Result.not_found(f"工具不存在: {tool_name}")

        http_config = await repository.get_protocol_http_by_id(tool.protocol_id)
        if not http_config:
            return Result.not_found("HTTP配置不存在")

        is_healthy, message = await mcp_tool_registry.health_check(
            http_config.http_url, http_config.timeout
        )

        # 更新状态
        statuses = {s.name: s for s in mcp_tool_registry.get_tool_statuses()}
        if tool_name in statuses:
            statuses[tool_name].status = "healthy" if is_healthy else "unhealthy"
            statuses[tool_name].error = None if is_healthy else message

        return Result.success(
            {
                "name": tool_name,
                "healthy": is_healthy,
                "message": message,
            }
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))
