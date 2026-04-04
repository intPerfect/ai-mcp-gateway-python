# -*- coding: utf-8 -*-
"""
Usage Service - 模型调用次数统计与限制
统计粒度：用户(key_id)-网关(gateway_id)级别
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config import get_settings
from app.infrastructure.cache.redis_client import RedisClient, get_redis
from app.infrastructure.database.models import McpUsageLog
from app.infrastructure.database import McpGatewayRepository
from app.utils.exceptions import RateLimitException

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class UsageInfo:
    """使用情况信息"""

    gateway_id: str
    key_id: str
    current_count: int
    limit: int
    remaining: int
    ttl_seconds: int
    window_hours: int


@dataclass
class UsageStats:
    """全局使用统计"""

    total_keys: int
    total_calls: int
    active_keys: int
    top_usage: List[Dict[str, Any]]


class UsageService:
    """使用统计服务"""

    def __init__(self, session: AsyncSession = None, redis: Redis = None):
        self.session = session
        self.repository = McpGatewayRepository(session) if session else None
        self._redis = redis
        self._redis_client: Optional[RedisClient] = None

    async def _get_redis_client(self) -> RedisClient:
        """获取 Redis 客户端"""
        if self._redis_client is None:
            if self._redis is None:
                self._redis = await get_redis()
            self._redis_client = RedisClient(self._redis)
        return self._redis_client

    async def check_and_increment(
        self,
        gateway_id: str,
        key_id: str,
        call_type: str,
        call_detail: str = None,
        session_id: str = None,
    ) -> int:
        """
        检查限制并增加计数（原子操作）
        如果超限则抛出异常，否则增加计数并返回新值

        Args:
            gateway_id: 网关ID
            key_id: API Key标识
            call_type: 调用类型 (llm/tool)
            call_detail: 调用详情
            session_id: 会话ID

        Returns:
            新的计数值

        Raises:
            RateLimitException: 超过限制时抛出
        """
        redis_client = await self._get_redis_client()

        limit = settings.default_rate_limit
        if self.repository:
            auth_info = await self.repository.get_gateway_auth_by_key_id(
                gateway_id, key_id
            )
            if auth_info and auth_info.rate_limit:
                limit = auth_info.rate_limit

        current_count = await redis_client.get_usage_count(gateway_id, key_id)

        if current_count >= limit:
            ttl_seconds = await redis_client.get_usage_ttl(gateway_id, key_id)
            hours = ttl_seconds // 3600
            minutes = (ttl_seconds % 3600) // 60
            raise RateLimitException(
                f"调用次数已达上限 ({current_count}/{limit})，"
                f"请在 {hours}小时{minutes}分钟后重试"
            )

        new_count = await redis_client.increment_usage(gateway_id, key_id)

        logger.info(
            f"[Usage] {gateway_id}/{key_id} {call_type} call, "
            f"count={new_count}/{limit}, detail={call_detail}"
        )

        if self.session:
            await self._write_usage_log(
                gateway_id=gateway_id,
                key_id=key_id,
                call_type=call_type,
                call_detail=call_detail,
                session_id=session_id,
                success=True,
            )

        return new_count

    async def record_usage(
        self,
        gateway_id: str,
        key_id: str,
        call_type: str,
        call_detail: str = None,
        session_id: str = None,
        success: bool = True,
    ) -> int:
        """
        记录调用次数（先检查限制再增加计数）

        Args:
            gateway_id: 网关ID
            key_id: API Key标识（用户标识）
            call_type: 调用类型 (llm/tool)
            call_detail: 调用详情（模型名或工具名）
            session_id: 会话ID
            success: 是否成功

        Returns:
            当前计数

        Raises:
            RateLimitException: 超过限制时抛出
        """
        redis_client = await self._get_redis_client()

        current_count = await redis_client.get_usage_count(gateway_id, key_id)
        limit = settings.default_rate_limit

        if self.repository:
            auth_info = await self.repository.get_gateway_auth_by_key_id(
                gateway_id, key_id
            )
            if auth_info and auth_info.rate_limit:
                limit = auth_info.rate_limit

        if current_count >= limit:
            ttl_seconds = await redis_client.get_usage_ttl(gateway_id, key_id)
            hours = ttl_seconds // 3600
            minutes = (ttl_seconds % 3600) // 60
            raise RateLimitException(
                f"调用次数已达上限 ({current_count}/{limit})，"
                f"请在 {hours}小时{minutes}分钟后重试"
            )

        count = await redis_client.increment_usage(gateway_id, key_id)

        logger.info(
            f"[Usage] {gateway_id}/{key_id} {call_type} call recorded, "
            f"count={count}, detail={call_detail}"
        )

        if self.session:
            await self._write_usage_log(
                gateway_id=gateway_id,
                key_id=key_id,
                call_type=call_type,
                call_detail=call_detail,
                session_id=session_id,
                success=success,
            )

        return count

    async def _write_usage_log(
        self,
        gateway_id: str,
        key_id: str,
        call_type: str,
        call_detail: str = None,
        session_id: str = None,
        success: bool = True,
    ):
        """写入使用日志到数据库"""
        log = McpUsageLog(
            gateway_id=gateway_id,
            key_id=key_id,
            session_id=session_id,
            call_type=call_type,
            call_detail=call_detail,
            call_time=datetime.now(),
            success=1 if success else 0,
        )
        self.session.add(log)
        await self.session.commit()

    async def check_usage_limit(
        self,
        gateway_id: str,
        key_id: str,
    ) -> UsageInfo:
        """
        检查使用限制

        Args:
            gateway_id: 网关ID
            key_id: API Key标识

        Returns:
            UsageInfo 包含当前用量和限制信息

        Raises:
            RateLimitException: 超过限制时抛出
        """
        redis_client = await self._get_redis_client()

        current_count = await redis_client.get_usage_count(gateway_id, key_id)
        ttl_seconds = await redis_client.get_usage_ttl(gateway_id, key_id)

        limit = settings.default_rate_limit

        if self.repository:
            auth_info = await self.repository.get_gateway_auth_by_key_id(
                gateway_id, key_id
            )
            if auth_info and auth_info.rate_limit:
                limit = auth_info.rate_limit

        remaining = limit - current_count

        usage_info = UsageInfo(
            gateway_id=gateway_id,
            key_id=key_id,
            current_count=current_count,
            limit=limit,
            remaining=remaining,
            ttl_seconds=ttl_seconds,
            window_hours=settings.usage_limit_window_hours,
        )

        if current_count >= limit:
            hours = ttl_seconds // 3600
            minutes = (ttl_seconds % 3600) // 60
            raise RateLimitException(
                f"调用次数已达上限 ({current_count}/{limit})，"
                f"请在 {hours}小时{minutes}分钟后重试"
            )

        return usage_info

    async def get_usage_info(
        self,
        gateway_id: str,
        key_id: str,
    ) -> UsageInfo:
        """
        获取使用情况信息（不检查限制）
        """
        redis_client = await self._get_redis_client()

        current_count = await redis_client.get_usage_count(gateway_id, key_id)
        ttl_seconds = await redis_client.get_usage_ttl(gateway_id, key_id)

        limit = settings.default_rate_limit

        if self.repository:
            auth_info = await self.repository.get_gateway_auth_by_key_id(
                gateway_id, key_id
            )
            if auth_info and auth_info.rate_limit:
                limit = auth_info.rate_limit

        return UsageInfo(
            gateway_id=gateway_id,
            key_id=key_id,
            current_count=current_count,
            limit=limit,
            remaining=limit - current_count,
            ttl_seconds=ttl_seconds,
            window_hours=settings.usage_limit_window_hours,
        )

    async def get_all_usage_stats(self) -> UsageStats:
        """
        获取全局使用统计（管理员用）
        """
        redis_client = await self._get_redis_client()

        keys = await redis_client.get_all_usage_keys()

        if not keys:
            return UsageStats(
                total_keys=0,
                total_calls=0,
                active_keys=0,
                top_usage=[],
            )

        stats = await redis_client.get_usage_stats_batch(keys)

        total_calls = sum(s["count"] for s in stats.values())
        active_keys = len([k for k, s in stats.items() if s["count"] > 0])

        top_usage = []
        sorted_keys = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)[
            :10
        ]
        for key, stat in sorted_keys:
            parts = key.split(":")
            if len(parts) >= 3:
                gateway_id = parts[1]
                key_id = parts[2]
                top_usage.append(
                    {
                        "gateway_id": gateway_id,
                        "key_id": key_id,
                        "count": stat["count"],
                        "ttl": stat["ttl"],
                    }
                )

        return UsageStats(
            total_keys=len(keys),
            total_calls=total_calls,
            active_keys=active_keys,
            top_usage=top_usage,
        )

    async def get_gateway_usage_list(
        self,
        gateway_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取指定网关的所有 Key 使用情况
        """
        redis_client = await self._get_redis_client()

        pattern = f"usage:{gateway_id}:*"
        keys = await self._redis.keys(pattern)

        if not keys:
            return []

        stats = await redis_client.get_usage_stats_batch(keys)

        result = []
        for key, stat in stats.items():
            parts = key.split(":")
            if len(parts) >= 3:
                key_id = parts[2]
                result.append(
                    {
                        "key_id": key_id,
                        "count": stat["count"],
                        "ttl": stat["ttl"],
                    }
                )

        return result

    async def reset_usage(
        self,
        gateway_id: str,
        key_id: str,
    ) -> bool:
        """
        重置使用计数（管理员用）
        """
        redis_client = await self._get_redis_client()
        return await redis_client.reset_usage(gateway_id, key_id)


async def get_usage_service(
    session: AsyncSession = None,
    redis: Redis = None,
) -> UsageService:
    """获取 UsageService 实例"""
    if redis is None:
        redis = await get_redis()
    return UsageService(session=session, redis=redis)
