# -*- coding: utf-8 -*-
"""
BaseRepository - 仓库基类
封装公共 session 属性和通用模式
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """数据仓库基类"""

    def __init__(self, session: AsyncSession):
        self.session = session
