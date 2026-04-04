# -*- coding: utf-8 -*-
"""
业务线管理 API 路由
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.result import Result, ResultCode
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories import BusinessLineRepository
from app.infrastructure.database.models import SysBusinessLine
from app.api.routers.auth import require_auth, UserInfo as CurrentUser
from app.api.schemas.user import BusinessLineCreate, BusinessLineUpdate

router = APIRouter(prefix="/api/business-lines", tags=["业务线管理"])


def bl_to_dict(bl: SysBusinessLine) -> dict:
    """业务线模型转字典"""
    return {
        "id": bl.id,
        "line_code": bl.line_code,
        "line_name": bl.line_name,
        "description": bl.description,
        "status": bl.status,
        "create_time": bl.create_time.isoformat() if bl.create_time else None,
        "update_time": bl.update_time.isoformat() if bl.update_time else None,
    }


@router.get("", response_model=Result[List[dict]])
async def list_business_lines(
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_auth),
):
    """获取所有业务线列表"""
    repo = BusinessLineRepository(session)
    business_lines = await repo.get_all_business_lines()
    return Result.success(data=[bl_to_dict(bl) for bl in business_lines])


@router.get("/{bl_id}", response_model=Result[dict])
async def get_business_line(
    bl_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_auth),
):
    """获取单个业务线"""
    repo = BusinessLineRepository(session)
    bl = await repo.get_business_line_by_id(bl_id)
    if not bl:
        return Result.not_found("业务线不存在")
    return Result.success(data=bl_to_dict(bl))


@router.post("", response_model=Result[dict])
async def create_business_line(
    request: BusinessLineCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_auth),
):
    """创建业务线（仅超级管理员）"""
    if "SUPER_ADMIN" not in current_user.roles:
        return Result.forbidden("仅超级管理员可创建业务线")

    repo = BusinessLineRepository(session)
    existing = await repo.get_business_line_by_code(request.line_code)
    if existing:
        return Result.error(ResultCode.DATA_EXISTS, "业务线编码已存在")

    bl = SysBusinessLine(
        line_code=request.line_code,
        line_name=request.line_name,
        description=request.description,
        status=1,
    )
    created = await repo.create_business_line(bl)
    return Result.success(data=bl_to_dict(created), message="创建成功")


@router.put("/{bl_id}", response_model=Result[dict])
async def update_business_line(
    bl_id: int,
    request: BusinessLineUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_auth),
):
    """更新业务线（仅超级管理员）"""
    if "SUPER_ADMIN" not in current_user.roles:
        return Result.forbidden("仅超级管理员可更新业务线")

    repo = BusinessLineRepository(session)
    update_data = {}
    if request.line_name is not None:
        update_data["line_name"] = request.line_name
    if request.description is not None:
        update_data["description"] = request.description
    if request.status is not None:
        update_data["status"] = request.status

    bl = await repo.update_business_line(bl_id, **update_data)
    if not bl:
        return Result.not_found("业务线不存在")
    return Result.success(data=bl_to_dict(bl), message="更新成功")


@router.delete("/{bl_id}", response_model=Result)
async def delete_business_line(
    bl_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_auth),
):
    """删除业务线（仅超级管理员）"""
    if "SUPER_ADMIN" not in current_user.roles:
        return Result.forbidden("仅超级管理员可删除业务线")

    repo = BusinessLineRepository(session)
    success = await repo.delete_business_line(bl_id)
    if not success:
        return Result.not_found("业务线不存在")
    return Result.success(message="删除成功")
