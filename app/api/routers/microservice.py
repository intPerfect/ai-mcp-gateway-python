# -*- coding: utf-8 -*-
"""
Microservice Router - 微服务管理路由
"""

import logging
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.infrastructure.database.models import (
    McpMicroservice, McpProtocolMapping, SysBusinessLine, McpGatewayMicroservice,
)
from app.api.schemas.microservice import (
    MicroserviceCreate,
    MicroserviceUpdate,
    ToolBindRequest,
    ToolEnabledRequest,
    ToolUpdateRequest,
)
from app.utils.result import Result, PageResult
from app.api.deps import (
    CurrentUser, UserInfo, DbSession,
    MicroserviceRepo, ToolRepo,
)
from app.api.routers.auth import require_auth, require_permission
from app.api.dependencies import (
    get_accessible_gateway_ids,
    check_tool_gateway_permission as _check_tool_gateway_permission,
    check_microservice_gateway_permission as _check_microservice_gateway_permission,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# 微服务管理接口
# ============================================


@router.get("/microservices")
async def list_microservices(
    current_user: CurrentUser,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    tool_repo: ToolRepo,
) -> PageResult:
    """获取微服务列表（按网关查看权限过滤）"""
    try:
        microservices = await microservice_repo.get_all_microservices()

        # 基于网关 can_read 权限过滤微服务
        accessible_gw_ids = await get_accessible_gateway_ids(current_user, db)
        if accessible_gw_ids is not None:
            accessible_set = set(accessible_gw_ids)
            stmt = select(McpGatewayMicroservice.microservice_id).where(
                McpGatewayMicroservice.gateway_id.in_(accessible_set),
                McpGatewayMicroservice.status == 1,
            )
            result = await db.execute(stmt)
            accessible_ms_ids = {row[0] for row in result.all()}

            microservices = [
                ms for ms in microservices if ms.id in accessible_ms_ids
            ]

        # 获取业务线映射
        business_line_map = {}

        # 获取每个微服务的工具数量
        result = []
        for ms in microservices:
            tools = await tool_repo.get_tools_by_microservice(ms.id)

            # 获取业务线名称
            if ms.business_line_id and ms.business_line_id not in business_line_map:
                bl = await db.get(SysBusinessLine, ms.business_line_id)
                if bl:
                    business_line_map[ms.business_line_id] = bl.line_name

            bl_name = business_line_map.get(ms.business_line_id) if ms.business_line_id else None
            if not bl_name:
                bl_name = ms.name

            ms_dict = {
                "id": ms.id,
                "name": ms.name,
                "http_base_url": ms.http_base_url,
                "description": ms.description,
                "business_line_id": ms.business_line_id,
                "business_line": bl_name,
                "health_status": ms.health_status,
                "last_check_time": ms.last_check_time.isoformat()
                if ms.last_check_time
                else None,
                "status": ms.status,
                "tool_count": len(tools),
                "create_time": ms.create_time.isoformat() if ms.create_time else None,
                "update_time": ms.update_time.isoformat() if ms.update_time else None,
            }
            result.append(ms_dict)

        return PageResult.of(data=result, total=len(result))
    except Exception as e:
        logger.error(f"获取微服务列表失败: {str(e)}")
        return PageResult.of(data=[], total=0, message=str(e))


@router.post("/microservices")
async def create_microservice(
    request: MicroserviceCreate,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("microservice:create")),
) -> Result:
    """创建微服务"""
    try:
        # 检查名称是否已存在
        existing = await microservice_repo.get_microservice_by_name(request.name)
        if existing:
            return Result.error("4001", f"微服务名称已存在: {request.name}")

        microservice = McpMicroservice(
            name=request.name,
            http_base_url=request.http_base_url,
            description=request.description,
            business_line_id=request.business_line_id,
            health_status="unknown",
            status=1,
        )

        created = await microservice_repo.create_microservice(microservice)

        # 获取业务线名称
        bl_name = None
        if created.business_line_id:
            bl = await db.get(SysBusinessLine, created.business_line_id)
            bl_name = bl.line_name if bl else None

        return Result.success(
            {
                "id": created.id,
                "name": created.name,
                "http_base_url": created.http_base_url,
                "description": created.description,
                "business_line": bl_name,
            }
        )
    except Exception as e:
        logger.error(f"创建微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/microservices/{microservice_id}")
async def update_microservice(
    microservice_id: int,
    request: MicroserviceUpdate,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("microservice:update")),
) -> Result:
    """更新微服务"""
    try:
        # 检查网关级别权限（can_update）
        await _check_microservice_gateway_permission(microservice_id, "update", current_user, db)

        # 如果要更新名称，检查是否重复
        if request.name:
            existing = await microservice_repo.get_microservice_by_name(request.name)
            if existing and existing.id != microservice_id:
                return Result.error("4001", f"微服务名称已存在: {request.name}")

        updated = await microservice_repo.update_microservice(
            microservice_id,
            name=request.name,
            http_base_url=request.http_base_url,
            description=request.description,
            business_line_id=request.business_line_id,
            status=request.status,
        )

        if not updated:
            return Result.not_found("微服务不存在")

        # 获取业务线名称
        bl_name = None
        if updated.business_line_id:
            bl = await db.get(SysBusinessLine, updated.business_line_id)
            bl_name = bl.line_name if bl else None

        return Result.success(
            {
                "id": updated.id,
                "name": updated.name,
                "http_base_url": updated.http_base_url,
                "description": updated.description,
                "business_line": bl_name,
                "status": updated.status,
            }
        )
    except Exception as e:
        logger.error(f"更新微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.delete("/microservices/{microservice_id}")
async def delete_microservice(
    microservice_id: int,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("microservice:delete")),
) -> Result:
    """删除微服务"""
    try:
        # 检查网关级别权限（can_delete）
        await _check_microservice_gateway_permission(microservice_id, "delete", current_user, db)

        success = await microservice_repo.delete_microservice(microservice_id)

        if not success:
            return Result.not_found("微服务不存在")

        return Result.success(message="删除成功")
    except Exception as e:
        logger.error(f"删除微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/microservices/{microservice_id}/check")
async def check_microservice_health(
    microservice_id: int,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("microservice:read")),
) -> Result:
    """微服务健康检查"""
    try:
        # 检查网关级别权限（can_read）
        await _check_microservice_gateway_permission(microservice_id, "read", current_user, db)

        microservice = await microservice_repo.get_microservice_by_id(microservice_id)

        if not microservice:
            return Result.not_found("微服务不存在")

        # 发送健康检查请求
        health_status = "unhealthy"
        check_message = ""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                check_url = microservice.http_base_url.rstrip("/")
                if not check_url.endswith("/health"):
                    check_url += "/health"

                response = await client.get(check_url)
                if response.status_code == 200:
                    health_status = "healthy"
                    check_message = "健康检查通过"
                else:
                    check_message = f"HTTP状态码: {response.status_code}"
        except httpx.TimeoutException:
            check_message = "请求超时"
        except httpx.ConnectError:
            check_message = "连接失败"
        except Exception as e:
            check_message = str(e)

        # 更新健康状态
        await microservice_repo.update_microservice_health(microservice_id, health_status)

        return Result.success(
            {"health_status": health_status, "message": check_message}
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return Result.internal_error(str(e))


@router.get("/microservices/{microservice_id}/tools")
async def get_microservice_tools(
    microservice_id: int,
    db: DbSession,
    microservice_repo: MicroserviceRepo,
    tool_repo: ToolRepo,
    current_user: UserInfo = Depends(require_permission("tool:read")),
) -> PageResult:
    """获取微服务的工具列表"""
    try:
        # 检查网关级别权限（can_read）
        await _check_microservice_gateway_permission(microservice_id, "read", current_user, db)

        microservice = await microservice_repo.get_microservice_by_id(microservice_id)
        if not microservice:
            return PageResult.of(data=[], total=0, message="微服务不存在")

        tools = await tool_repo.get_tools_by_microservice(microservice_id)

        result = []
        for tool in tools:
            result.append(
                {
                    "id": tool.id,
                    "tool_id": tool.tool_id,
                    "tool_name": tool.tool_name,
                    "tool_description": tool.tool_description,
                    "microservice_id": tool.microservice_id,
                    "microservice_name": microservice.name,
                    "enabled": tool.enabled,
                    "call_status": tool.call_status,
                    "last_call_time": tool.last_call_time.isoformat()
                    if tool.last_call_time
                    else None,
                    "last_call_code": tool.last_call_code,
                    "call_count": tool.call_count or 0,
                    "error_count": tool.error_count or 0,
                }
            )

        return PageResult.of(data=result, total=len(result))
    except Exception as e:
        logger.error(f"获取微服务工具列表失败: {str(e)}")
        return PageResult.of(data=[], total=0, message=str(e))


# ============================================
# 工具管理接口
# ============================================


@router.get("/tools/all")
async def list_all_tools(
    db: DbSession,
    tool_repo: ToolRepo,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("tool:read")),
) -> PageResult:
    """获取所有工具列表（按网关查看权限过滤，包含业务线信息）"""
    try:
        tools = await tool_repo.get_all_tools()

        # 基于网关 can_read 权限过滤工具
        accessible_gw_ids = await get_accessible_gateway_ids(current_user, db)
        if accessible_gw_ids is not None:
            accessible_set = set(accessible_gw_ids)
            tools = [t for t in tools if t.gateway_id in accessible_set]

        # 构建微服务映射
        microservices = await microservice_repo.get_all_microservices()
        ms_map = {ms.id: ms for ms in microservices}

        # 构建业务线映射（确保 business_line 不为空）
        business_line_map = {}
        for ms in microservices:
            if ms.business_line_id and ms.business_line_id not in business_line_map:
                bl = await db.get(SysBusinessLine, ms.business_line_id)
                if bl:
                    business_line_map[ms.business_line_id] = bl.line_name

        result = []
        for tool in tools:
            ms = ms_map.get(tool.microservice_id) if tool.microservice_id else None
            bl_name = None
            if ms and ms.business_line_id:
                bl_name = business_line_map.get(ms.business_line_id)
            if not bl_name:
                bl_name = ms.name if ms else "未分类"

            result.append(
                {
                    "id": tool.id,
                    "tool_id": tool.tool_id,
                    "tool_name": tool.tool_name,
                    "tool_description": tool.tool_description,
                    "microservice_id": tool.microservice_id,
                    "microservice_name": ms.name if ms else None,
                    "business_line": bl_name,
                    "enabled": tool.enabled,
                    "call_status": tool.call_status,
                    "last_call_time": tool.last_call_time.isoformat()
                    if tool.last_call_time
                    else None,
                    "last_call_code": tool.last_call_code,
                    "call_count": tool.call_count or 0,
                    "error_count": tool.error_count or 0,
                }
            )

        return PageResult.of(data=result, total=len(result))
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        return PageResult.of(data=[], total=0, message=str(e))


@router.put("/tools/{tool_id}/bind")
async def bind_tool(
    tool_id: int,
    request: ToolBindRequest,
    db: DbSession,
    tool_repo: ToolRepo,
    microservice_repo: MicroserviceRepo,
    current_user: UserInfo = Depends(require_permission("tool:update")),
) -> Result:
    """绑定工具到微服务"""
    try:
        tool = await tool_repo.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")

        # 检查网关级别权限（can_update）
        await _check_tool_gateway_permission(tool, "update", current_user, db)

        microservice = await microservice_repo.get_microservice_by_id(request.microservice_id)
        if not microservice:
            return Result.not_found("微服务不存在")

        await tool_repo.bind_tool_to_microservice(tool_id, request.microservice_id)

        return Result.success(message=f"工具已绑定到微服务: {microservice.name}")
    except Exception as e:
        logger.error(f"绑定工具失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/tools/{tool_id}/enabled")
async def update_tool_enabled(
    tool_id: int,
    request: ToolEnabledRequest,
    db: DbSession,
    tool_repo: ToolRepo,
    current_user: UserInfo = Depends(require_permission("tool:update")),
) -> Result:
    """更新工具启用状态"""
    try:
        tool = await tool_repo.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")

        # 检查网关级别权限（can_update）
        await _check_tool_gateway_permission(tool, "update", current_user, db)

        await tool_repo.update_tool_enabled(tool_id, request.enabled)

        status_text = "启用" if request.enabled == 1 else "禁用"
        return Result.success(message=f"工具已{status_text}")
    except Exception as e:
        logger.error(f"更新工具状态失败: {str(e)}")
        return Result.internal_error(str(e))


@router.get("/tools/{tool_id}/detail")
async def get_tool_detail(
    tool_id: int,
    db: DbSession,
    tool_repo: ToolRepo,
    current_user: UserInfo = Depends(require_permission("tool:read")),
) -> Result:
    """获取工具详情（含HTTP配置和参数映射）"""
    try:
        tool = await tool_repo.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")

        # 检查网关级别权限（can_read）
        await _check_tool_gateway_permission(tool, "read", current_user, db)

        # 获取HTTP协议配置
        http_config = await tool_repo.get_protocol_http_by_id(tool.protocol_id)
        http_data = None
        if http_config:
            http_data = {
                "http_url": http_config.http_url,
                "http_method": http_config.http_method,
                "http_headers": http_config.http_headers,
                "timeout": http_config.timeout,
                "retry_times": http_config.retry_times,
            }

        # 获取参数映射
        mappings = await tool_repo.get_protocol_mappings(tool.protocol_id)
        params_data = [
            {
                "id": m.id,
                "param_location": m.param_location,
                "field_name": m.field_name,
                "field_type": m.field_type,
                "field_desc": m.field_desc,
                "is_required": m.is_required,
                "default_value": m.default_value,
                "enum_values": m.enum_values,
                "example_value": m.example_value,
                "sort_order": m.sort_order,
            }
            for m in mappings
        ]

        return Result.success(
            {
                "tool_id": tool.tool_id,
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "protocol_id": tool.protocol_id,
                "http_config": http_data,
                "parameters": params_data,
            }
        )
    except Exception as e:
        logger.error(f"获取工具详情失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: int,
    request: ToolUpdateRequest,
    db: DbSession,
    tool_repo: ToolRepo,
    current_user: UserInfo = Depends(require_permission("tool:update")),
) -> Result:
    """更新工具信息（含HTTP配置和参数映射）"""
    try:
        tool = await tool_repo.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")

        # 检查网关级别权限（can_update）
        await _check_tool_gateway_permission(tool, "update", current_user, db)

        # 更新工具基本信息
        update_data = {}
        if request.tool_name is not None:
            update_data["tool_name"] = request.tool_name
        if request.tool_description is not None:
            update_data["tool_description"] = request.tool_description
        if update_data:
            await tool_repo.update_tool(tool_id, **update_data)

        # 更新HTTP协议配置
        if request.http_config is not None:
            http_update = {}
            if request.http_config.http_url is not None:
                http_update["http_url"] = request.http_config.http_url
            if request.http_config.http_method is not None:
                http_update["http_method"] = request.http_config.http_method
            if request.http_config.http_headers is not None:
                http_update["http_headers"] = request.http_config.http_headers
            if request.http_config.timeout is not None:
                http_update["timeout"] = request.http_config.timeout
            if request.http_config.retry_times is not None:
                http_update["retry_times"] = request.http_config.retry_times
            if http_update:
                await tool_repo.update_protocol_http(tool.protocol_id, **http_update)

        # 更新参数映射（全量替换）
        if request.parameters is not None:
            await tool_repo.delete_protocol_mappings(tool.protocol_id)
            if request.parameters:
                new_mappings = [
                    McpProtocolMapping(
                        protocol_id=tool.protocol_id,
                        param_location=p.param_location,
                        field_name=p.field_name,
                        field_type=p.field_type,
                        field_desc=p.field_desc,
                        is_required=p.is_required,
                        default_value=p.default_value,
                        enum_values=p.enum_values,
                        example_value=p.example_value,
                        sort_order=p.sort_order,
                    )
                    for p in request.parameters
                ]
                await tool_repo.batch_create_protocol_mappings(new_mappings)

        return Result.success(message="更新成功")
    except Exception as e:
        logger.error(f"更新工具失败: {str(e)}")
        return Result.internal_error(str(e))
