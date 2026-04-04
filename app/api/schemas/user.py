# -*- coding: utf-8 -*-
"""
User/Role Schemas - 用户/角色相关请求/响应模型
从路由文件中提取的内联 Schema
"""

from typing import Optional, List
from pydantic import BaseModel


# 从 business_line.py 提取
class BusinessLineCreate(BaseModel):
    line_name: str
    line_code: str
    description: Optional[str] = None


class BusinessLineUpdate(BaseModel):
    line_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


# 从 role.py 提取
class DataPermissionRequest(BaseModel):
    """数据权限请求"""
    business_lines: List[str] = []
    gateway_ids: List[str] = []
    microservice_ids: List[int] = []
    chat_access: bool = True
