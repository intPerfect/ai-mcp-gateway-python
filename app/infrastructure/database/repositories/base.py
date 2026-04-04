# -*- coding: utf-8 -*-
"""
BaseRepository - 仓库基类
封装公共 session 属性和通用模式
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """数据仓库基类，封装公共的数据库会话属性。

    所有具体的 Repository 应继承此类，并通过 ``self.session``
    执行数据库操作。
    """

    def __init__(self, session: AsyncSession):
        """初始化仓库。

        Args:
            session: SQLAlchemy 异步数据库会话。
        """
        self.session = session
