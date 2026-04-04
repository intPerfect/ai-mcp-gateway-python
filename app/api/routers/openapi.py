# -*- coding: utf-8 -*-
"""
OpenAPI Router - OpenAPI导入路由
精简后的路由层，只负责请求响应处理
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import (
    McpGatewayTool,
    McpProtocolHttp,
    McpProtocolMapping,
)
from app.infrastructure.database.repositories import ToolRepository
from app.api.schemas.openapi import OpenAPIImportRequest
from app.domain.protocol.openapi import (
    parse_openapi_spec,
    fetch_openapi_spec,
    build_preview_data,
)
from app.utils.result import Result
from app.api.routers.auth import require_permission, UserInfo as CurrentUser
from app.domain.rbac.service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/openapi/import")
async def import_openapi(
    request: OpenAPIImportRequest,
    current_user: CurrentUser = Depends(require_permission("tool:create")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    导入OpenAPI规范并生成MCP工具配置
    需要有tool:create权限，且对指定gateway_id有create权限
    """
    try:
        # 检查网关级别权限
        if "SUPER_ADMIN" not in current_user.roles:
            rbac_service = PermissionService(db)
            has_perm = await rbac_service.check_gateway_permission(
                current_user.id, request.gateway_id, "create"
            )
            if not has_perm:
                return Result.error("FORBIDDEN", "无权限操作此网关")

        # 获取OpenAPI规范
        if request.openapi_url:
            spec = await fetch_openapi_spec(request.openapi_url)
        elif request.openapi_spec:
            spec = request.openapi_spec
        else:
            raise HTTPException(
                status_code=400, detail="必须提供 openapi_url 或 openapi_spec"
            )

        # 解析OpenAPI规范
        tools = parse_openapi_spec(spec)

        if not tools:
            return Result.success({"message": "未发现可导入的API", "tools": []})

        # 导入到数据库
        imported = []
        repository = ToolRepository(db)

        for tool in tools:
            try:
                existing = await repository.get_tool_by_name(
                    request.gateway_id, tool.name
                )
                if existing:
                    logger.info(f"工具已存在，跳过: {tool.name}")
                    continue

                # 创建HTTP协议配置
                http_config = McpProtocolHttp(
                    protocol_id=0,
                    http_url=f"{request.service_url.rstrip('/')}{tool.path}",
                    http_method=tool.method,
                    http_headers=None,
                    timeout=30000,
                    status=1,
                )
                db.add(http_config)
                await db.flush()

                protocol_id = http_config.id
                http_config.protocol_id = protocol_id

                # 创建工具配置
                tool_config = McpGatewayTool(
                    gateway_id=request.gateway_id,
                    tool_id=protocol_id,
                    tool_name=tool.name,
                    tool_type="function",
                    tool_description=tool.description,
                    tool_version="1.0.0",
                    protocol_id=protocol_id,
                    protocol_type="http",
                    microservice_id=request.microservice_id,
                )
                db.add(tool_config)

                # 创建参数映射
                for idx, param in enumerate(tool.parameters):
                    param_name = param.get("name", "")
                    param_in = param.get("param_in", "query")
                    param_desc = param.get("description", "")
                    param_type = param.get("type", "string")
                    param_required = param.get("required", False)
                    param_default = param.get("default")
                    param_enum = param.get("enum")
                    param_example = param.get("example")

                    if param_type.startswith("array"):
                        field_type = "array"
                    else:
                        field_type = param_type

                    mapping = McpProtocolMapping(
                        protocol_id=protocol_id,
                        param_location=param_in,
                        field_name=param_name,
                        field_type=field_type,
                        field_desc=param_desc,
                        is_required=1 if param_required else 0,
                        default_value=str(param_default)
                        if param_default is not None
                        else None,
                        enum_values=str(param_enum) if param_enum else None,
                        example_value=str(param_example)
                        if param_example is not None
                        else None,
                        sort_order=idx,
                    )
                    db.add(mapping)

                imported.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "method": tool.method,
                        "path": tool.path,
                        "param_count": len(tool.parameters),
                    }
                )

            except Exception as e:
                logger.error(f"导入工具失败: {tool.name} - {str(e)}")

        await db.commit()

        return Result.success(
            {"message": f"成功导入 {len(imported)} 个工具", "tools": imported}
        )

    except Exception as e:
        logger.error(f"导入OpenAPI失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openapi/preview")
async def preview_openapi(
    openapi_url: str,
    service_url: str,
    current_user: CurrentUser = Depends(require_permission("tool:read")),
):
    """预览OpenAPI规范解析结果（需要tool:read权限）"""
    try:
        spec = await fetch_openapi_spec(openapi_url)
        tools = parse_openapi_spec(spec)
        preview = build_preview_data(tools, service_url)

        return Result.success({"total": len(preview), "tools": preview})

    except Exception as e:
        logger.error(f"预览OpenAPI失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
