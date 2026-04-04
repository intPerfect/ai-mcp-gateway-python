# -*- coding: utf-8 -*-
"""
Permission Router - 权限管理API路由
"""
import logging
from typing import List
from fastapi import APIRouter

from app.infrastructure.database.models import SysPermission, SysResource
from app.domain.rbac import (
    PermissionInfo, ResourceInfo, 
    PermissionTreeNode, ResourcePermissionGroup, DataScopeTreeNode
)
from app.utils.result import Result
from app.api.deps import (
    CurrentUser,
    PermissionRepo, MicroserviceRepo, GatewayRepo, BusinessLineRepo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/permissions", tags=["权限管理"])


def perm_to_info(perm: SysPermission, resource_name: str = None) -> PermissionInfo:
    """转换ORM模型到Info模型"""
    return PermissionInfo(
        id=perm.id,
        permission_code=perm.permission_code,
        permission_name=perm.permission_name,
        resource_id=perm.resource_id,
        resource_name=resource_name,
        action=perm.action,
        description=perm.description,
        status=perm.status
    )


def resource_to_info(resource: SysResource, children: List[ResourceInfo] = None) -> ResourceInfo:
    """转换ORM模型到Info模型"""
    return ResourceInfo(
        id=resource.id,
        resource_code=resource.resource_code,
        resource_name=resource.resource_name,
        resource_type=resource.resource_type,
        parent_id=resource.parent_id,
        api_path=resource.api_path,
        icon=resource.icon,
        sort_order=resource.sort_order,
        status=resource.status,
        children=children or []
    )


@router.get("", response_model=Result[List[PermissionInfo]])
async def list_permissions(
    current_user: CurrentUser,
    permission_repo: PermissionRepo,
    resource_id: int = None,
):
    """获取权限列表"""
    if resource_id:
        permissions = await permission_repo.get_permissions_by_resource(resource_id)
    else:
        permissions = await permission_repo.get_all_permissions()
    
    result = []
    for perm in permissions:
        resource_name = None
        resource = await permission_repo.get_resource_by_id(perm.resource_id)
        if resource:
            resource_name = resource.resource_name
        
        result.append(perm_to_info(perm, resource_name))
    
    return Result.success(data=result)


@router.get("/resources", response_model=Result[List[ResourceInfo]])
async def list_resources(
    current_user: CurrentUser,
    permission_repo: PermissionRepo,
):
    """获取资源列表"""
    resources = await permission_repo.get_all_resources()
    
    # 构建树形结构
    def build_tree(parent_id: int = 0) -> List[ResourceInfo]:
        result = []
        for res in resources:
            if res.parent_id == parent_id:
                children = build_tree(res.id)
                result.append(resource_to_info(res, children if children else None))
        return result
    
    result = build_tree()
    
    return Result.success(data=result)


@router.get("/my", response_model=Result[List[str]])
async def get_my_permissions(
    current_user: CurrentUser,
    permission_repo: PermissionRepo,
):
    """获取当前用户权限列表"""
    permissions = await permission_repo.get_user_permissions(current_user.id)
    perm_codes = [p.permission_code for p in permissions]
    
    return Result.success(data=perm_codes)


@router.get("/my/menus", response_model=Result[List[ResourceInfo]])
async def get_my_menus(
    current_user: CurrentUser,
    permission_repo: PermissionRepo,
):
    """获取当前用户菜单"""
    # 获取用户权限
    permissions = await permission_repo.get_user_permissions(current_user.id)
    perm_resource_ids = [p.resource_id for p in permissions]
    
    # 获取所有资源
    resources = await permission_repo.get_all_resources()
    
    # 超级管理员返回全部菜单
    if "SUPER_ADMIN" in current_user.roles:
        menu_resources = [r for r in resources if r.resource_type == 'menu']
    else:
        # 只返回有权限的菜单
        menu_resources = [
            r for r in resources 
            if r.resource_type == 'menu' and r.id in perm_resource_ids
        ]
    
    # 构建菜单树
    def build_menu_tree(parent_id: int = 0) -> List[ResourceInfo]:
        result = []
        for res in menu_resources:
            if res.parent_id == parent_id:
                children = build_menu_tree(res.id)
                result.append(resource_to_info(res, children if children else None))
        return result
    
    result = build_menu_tree()
    
    return Result.success(data=result)


@router.get("/tree", response_model=Result[List[ResourcePermissionGroup]])
async def get_permission_tree(
    current_user: CurrentUser,
    permission_repo: PermissionRepo,
):
    """获取权限树（按资源分组）"""
    # 获取所有资源
    resources = await permission_repo.get_all_resources()
    # 获取所有权限
    permissions = await permission_repo.get_all_permissions()
    
    # 按资源分组构建权限树
    result = []
    for res in resources:
        # 获取该资源下的所有权限
        res_perms = [p for p in permissions if p.resource_id == res.id]
        if not res_perms:
            continue
        
        perm_nodes = []
        for perm in res_perms:
            perm_nodes.append(PermissionTreeNode(
                id=perm.id,
                code=perm.permission_code,
                name=perm.permission_name,
                resource_id=res.id,
                resource_name=res.resource_name,
                action=perm.action,
                checked=False
            ))
        
        result.append(ResourcePermissionGroup(
            resource_id=res.id,
            resource_code=res.resource_code,
            resource_name=res.resource_name,
            permissions=perm_nodes
        ))
    
    return Result.success(data=result)


@router.get("/data-scopes/tree", response_model=Result[List[DataScopeTreeNode]])
async def get_data_scope_tree(
    current_user: CurrentUser,
    microservice_repo: MicroserviceRepo,
    gateway_repo: GatewayRepo,
    business_line_repo: BusinessLineRepo,
):
    """获取数据权限树（业务线-微服务-网关）"""
    # 获取所有微服务
    microservices = await microservice_repo.get_all_microservices()
    # 获取所有网关
    gateways = await gateway_repo.get_all_gateways()
    
    # 获取业务线映射 {id: name}
    all_bl = await business_line_repo.get_all_business_lines()
    bl_map = {bl.id: bl.line_name for bl in all_bl}
    
    # 按业务线分组
    business_line_map = {}  # {业务线名: {microservices: [], gateways: []}}
    
    for ms in microservices:
        bl = bl_map.get(ms.business_line_id) if ms.business_line_id else None or "未分类"
        if bl not in business_line_map:
            business_line_map[bl] = {"microservices": [], "gateways": []}
        business_line_map[bl]["microservices"].append(ms)
    
    for gw in gateways:
        # 网关暂时归入"默认"业务线
        bl = "默认网关"
        if bl not in business_line_map:
            business_line_map[bl] = {"microservices": [], "gateways": []}
        business_line_map[bl]["gateways"].append(gw)
    
    # 构建树
    result = []
    for bl_name, bl_data in business_line_map.items():
        # 业务线节点
        bl_node = DataScopeTreeNode(
            id=f"bl_{bl_name}",
            name=bl_name,
            type="business_line",
            children=[],
            checked=False
        )
        
        # 微服务子节点
        for ms in bl_data["microservices"]:
            ms_node = DataScopeTreeNode(
                id=f"ms_{ms.id}",
                name=ms.name,
                type="microservice",
                parent_id=bl_node.id,
                children=[],
                checked=False
            )
            bl_node.children.append(ms_node)
        
        # 网关子节点
        for gw in bl_data["gateways"]:
            gw_node = DataScopeTreeNode(
                id=f"gw_{gw.gateway_id}",
                name=gw.gateway_name,
                type="gateway",
                parent_id=bl_node.id,
                children=[],
                checked=False
            )
            bl_node.children.append(gw_node)
        
        result.append(bl_node)
    
    return Result.success(data=result)


@router.get("/data-scopes/options", response_model=Result[dict])
async def get_data_scope_options(
    current_user: CurrentUser,
    microservice_repo: MicroserviceRepo,
    gateway_repo: GatewayRepo,
    business_line_repo: BusinessLineRepo,
):
    """获取数据权限选项（业务线、网关列表）"""
    # 获取所有微服务
    microservices = await microservice_repo.get_all_microservices()
    # 获取所有网关
    gateways = await gateway_repo.get_all_gateways()
    
    # 获取业务线映射
    all_bl = await business_line_repo.get_all_business_lines()
    bl_map = {bl.id: bl.line_name for bl in all_bl}
    
    # 获取业务线列表（去重）
    business_lines = list(set([bl_map.get(ms.business_line_id) for ms in microservices if ms.business_line_id and bl_map.get(ms.business_line_id)]))
    business_lines.sort()
    
    # 网关列表
    gateway_list = [{"id": gw.gateway_id, "name": gw.gateway_name} for gw in gateways]
    
    # 微服务列表
    microservice_list = [{"id": ms.id, "name": ms.name, "business_line": bl_map.get(ms.business_line_id) or "未分类"} for ms in microservices]
    
    return Result.success(data={
        "business_lines": business_lines,
        "gateways": gateway_list,
        "microservices": microservice_list
    })
