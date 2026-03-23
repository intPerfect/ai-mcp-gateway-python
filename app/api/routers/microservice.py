# -*- coding: utf-8 -*-
"""
Microservice Router - 微服务管理路由
"""
import logging
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database import McpGatewayRepository
from app.infrastructure.database.models import McpMicroservice
from app.api.schemas.microservice import (
    MicroserviceCreate,
    MicroserviceUpdate,
    ToolBindRequest,
    ToolEnabledRequest
)
from app.utils.result import Result

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# 微服务管理接口
# ============================================

@router.get("/microservices")
async def list_microservices(
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """获取微服务列表"""
    try:
        repository = McpGatewayRepository(db)
        microservices = await repository.get_all_microservices()
        
        # 获取每个微服务的工具数量
        result = []
        for ms in microservices:
            tools = await repository.get_tools_by_microservice(ms.id)
            ms_dict = {
                "id": ms.id,
                "name": ms.name,
                "http_base_url": ms.http_base_url,
                "description": ms.description,
                "business_line": ms.business_line,
                "health_status": ms.health_status,
                "last_check_time": ms.last_check_time.isoformat() if ms.last_check_time else None,
                "status": ms.status,
                "tool_count": len(tools),
                "create_time": ms.create_time.isoformat() if ms.create_time else None,
                "update_time": ms.update_time.isoformat() if ms.update_time else None
            }
            result.append(ms_dict)
        
        return Result.success(result)
    except Exception as e:
        logger.error(f"获取微服务列表失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/microservices")
async def create_microservice(
    request: MicroserviceCreate,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """创建微服务"""
    try:
        repository = McpGatewayRepository(db)
        
        # 检查名称是否已存在
        existing = await repository.get_microservice_by_name(request.name)
        if existing:
            return Result.error("4001", f"微服务名称已存在: {request.name}")
        
        microservice = McpMicroservice(
            name=request.name,
            http_base_url=request.http_base_url,
            description=request.description,
            business_line=request.business_line,
            health_status="unknown",
            status=1
        )
        
        created = await repository.create_microservice(microservice)
        
        return Result.success({
            "id": created.id,
            "name": created.name,
            "http_base_url": created.http_base_url,
            "description": created.description,
            "business_line": created.business_line
        })
    except Exception as e:
        logger.error(f"创建微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/microservices/{microservice_id}")
async def update_microservice(
    microservice_id: int,
    request: MicroserviceUpdate,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """更新微服务"""
    try:
        repository = McpGatewayRepository(db)
        
        # 如果要更新名称，检查是否重复
        if request.name:
            existing = await repository.get_microservice_by_name(request.name)
            if existing and existing.id != microservice_id:
                return Result.error("4001", f"微服务名称已存在: {request.name}")
        
        updated = await repository.update_microservice(
            microservice_id,
            name=request.name,
            http_base_url=request.http_base_url,
            description=request.description,
            business_line=request.business_line,
            status=request.status
        )
        
        if not updated:
            return Result.not_found("微服务不存在")
        
        return Result.success({
            "id": updated.id,
            "name": updated.name,
            "http_base_url": updated.http_base_url,
            "description": updated.description,
            "business_line": updated.business_line,
            "status": updated.status
        })
    except Exception as e:
        logger.error(f"更新微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.delete("/microservices/{microservice_id}")
async def delete_microservice(
    microservice_id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """删除微服务"""
    try:
        repository = McpGatewayRepository(db)
        
        # 先解绑所有工具
        tools = await repository.get_tools_by_microservice(microservice_id)
        for tool in tools:
            await repository.unbind_tool(tool.tool_id)
        
        # 删除微服务
        success = await repository.delete_microservice(microservice_id)
        
        if not success:
            return Result.not_found("微服务不存在")
        
        return Result.success(message="删除成功")
    except Exception as e:
        logger.error(f"删除微服务失败: {str(e)}")
        return Result.internal_error(str(e))


@router.post("/microservices/{microservice_id}/check")
async def check_microservice_health(
    microservice_id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """微服务健康检查"""
    try:
        repository = McpGatewayRepository(db)
        microservice = await repository.get_microservice_by_id(microservice_id)
        
        if not microservice:
            return Result.not_found("微服务不存在")
        
        # 发送健康检查请求
        health_status = "unhealthy"
        check_message = ""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试访问基础URL或健康检查端点
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
        await repository.update_microservice_health(microservice_id, health_status)
        
        return Result.success({
            "health_status": health_status,
            "message": check_message
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return Result.internal_error(str(e))


@router.get("/microservices/{microservice_id}/tools")
async def get_microservice_tools(
    microservice_id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """获取微服务的工具列表"""
    try:
        repository = McpGatewayRepository(db)
        
        microservice = await repository.get_microservice_by_id(microservice_id)
        if not microservice:
            return Result.not_found("微服务不存在")
        
        tools = await repository.get_tools_by_microservice(microservice_id)
        
        result = []
        for tool in tools:
            result.append({
                "id": tool.id,
                "tool_id": tool.tool_id,
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "microservice_id": tool.microservice_id,
                "microservice_name": microservice.name,
                "enabled": tool.enabled,
                "call_status": tool.call_status,
                "last_call_time": tool.last_call_time.isoformat() if tool.last_call_time else None,
                "last_call_code": tool.last_call_code,
                "call_count": tool.call_count or 0,
                "error_count": tool.error_count or 0
            })
        
        return Result.success(result)
    except Exception as e:
        logger.error(f"获取微服务工具列表失败: {str(e)}")
        return Result.internal_error(str(e))


# ============================================
# 工具管理接口
# ============================================

@router.get("/tools/all")
async def list_all_tools(
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """获取所有工具列表（包含微服务信息）"""
    try:
        repository = McpGatewayRepository(db)
        tools = await repository.get_all_tools()
        microservices = await repository.get_all_microservices()
        
        # 构建微服务ID到名称的映射
        ms_map = {ms.id: ms.name for ms in microservices}
        
        result = []
        for tool in tools:
            result.append({
                "id": tool.id,
                "tool_id": tool.tool_id,
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "microservice_id": tool.microservice_id,
                "microservice_name": ms_map.get(tool.microservice_id),
                "enabled": tool.enabled,
                "call_status": tool.call_status,
                "last_call_time": tool.last_call_time.isoformat() if tool.last_call_time else None,
                "last_call_code": tool.last_call_code,
                "call_count": tool.call_count or 0,
                "error_count": tool.error_count or 0
            })
        
        return Result.success(result)
    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        return Result.internal_error(str(e))


@router.get("/tools/unbind")
async def list_unbind_tools(
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """获取未绑定微服务的工具列表"""
    try:
        repository = McpGatewayRepository(db)
        tools = await repository.get_unbind_tools()
        
        result = []
        for tool in tools:
            result.append({
                "id": tool.id,
                "tool_id": tool.tool_id,
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "enabled": tool.enabled,
                "call_status": tool.call_status
            })
        
        return Result.success(result)
    except Exception as e:
        logger.error(f"获取未绑定工具列表失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/tools/{tool_id}/bind")
async def bind_tool(
    tool_id: int,
    request: ToolBindRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """绑定工具到微服务"""
    try:
        repository = McpGatewayRepository(db)
        
        # 检查工具是否存在
        tool = await repository.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")
        
        # 检查微服务是否存在
        microservice = await repository.get_microservice_by_id(request.microservice_id)
        if not microservice:
            return Result.not_found("微服务不存在")
        
        await repository.bind_tool_to_microservice(tool_id, request.microservice_id)
        
        return Result.success(message=f"工具已绑定到微服务: {microservice.name}")
    except Exception as e:
        logger.error(f"绑定工具失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/tools/{tool_id}/unbind")
async def unbind_tool(
    tool_id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """解绑工具"""
    try:
        repository = McpGatewayRepository(db)
        
        tool = await repository.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")
        
        await repository.unbind_tool(tool_id)
        
        return Result.success(message="工具已解绑")
    except Exception as e:
        logger.error(f"解绑工具失败: {str(e)}")
        return Result.internal_error(str(e))


@router.put("/tools/{tool_id}/enabled")
async def update_tool_enabled(
    tool_id: int,
    request: ToolEnabledRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Result:
    """更新工具启用状态"""
    try:
        repository = McpGatewayRepository(db)
        
        tool = await repository.get_tool_by_id(tool_id)
        if not tool:
            return Result.not_found("工具不存在")
        
        await repository.update_tool_enabled(tool_id, request.enabled)
        
        status_text = "启用" if request.enabled == 1 else "禁用"
        return Result.success(message=f"工具已{status_text}")
    except Exception as e:
        logger.error(f"更新工具状态失败: {str(e)}")
        return Result.internal_error(str(e))
