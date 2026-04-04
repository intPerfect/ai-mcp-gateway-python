# -*- coding: utf-8 -*-
"""
Redis Client - Redis connection management
"""

import json
import logging
from typing import Optional, List, Dict, Any
from redis import asyncio as aioredis
from redis.asyncio import Redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    Get Redis client instance (lazy initialization)
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(f"Redis connected: {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    return _redis_client


async def close_redis():
    """
    Close Redis connection
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


class RedisClient:
    """
    Redis client wrapper for usage counting
    """

    USAGE_KEY_PREFIX = "usage"
    WINDOW_SECONDS = settings.usage_limit_window_hours * 3600

    def __init__(self, redis: Redis):
        self.redis = redis

    def _build_usage_key(self, gateway_id: str, key_id: str) -> str:
        """
        Build Redis key for usage counter
        Key format: usage:{gateway_id}:{key_id}
        """
        return f"{self.USAGE_KEY_PREFIX}:{gateway_id}:{key_id}"

    async def increment_usage(self, gateway_id: str, key_id: str) -> int:
        """
        Increment usage counter, return current count
        Auto-set TTL on first increment
        """
        key = self._build_usage_key(gateway_id, key_id)
        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, self.WINDOW_SECONDS)
            logger.debug(f"Set TTL for {key}: {self.WINDOW_SECONDS}s")

        return count

    async def get_usage_count(self, gateway_id: str, key_id: str) -> int:
        """
        Get current usage count
        """
        key = self._build_usage_key(gateway_id, key_id)
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def get_usage_ttl(self, gateway_id: str, key_id: str) -> int:
        """
        Get remaining TTL in seconds
        """
        key = self._build_usage_key(gateway_id, key_id)
        ttl = await self.redis.ttl(key)
        return ttl if ttl > 0 else 0

    async def reset_usage(self, gateway_id: str, key_id: str) -> bool:
        """
        Reset usage counter
        """
        key = self._build_usage_key(gateway_id, key_id)
        await self.redis.delete(key)
        return True

    async def get_all_usage_keys(self) -> list:
        """
        Get all usage keys (for admin stats)
        """
        pattern = f"{self.USAGE_KEY_PREFIX}:*"
        keys = await self.redis.keys(pattern)
        return keys

    async def get_usage_stats_batch(self, keys: list) -> dict:
        """
        Get usage stats for multiple keys
        Returns dict: {key: {count, ttl}}
        """
        if not keys:
            return {}

        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(key)
            pipe.ttl(key)
        results = await pipe.execute()

        stats = {}
        for i, key in enumerate(keys):
            count = int(results[i * 2]) if results[i * 2] else 0
            ttl = results[i * 2 + 1] if results[i * 2 + 1] > 0 else 0
            stats[key] = {"count": count, "ttl": ttl}

        return stats


class PermissionCache:
    """
    用户权限 Redis 缓存 (Cache Aside 算法)

    缓存结构:
      perm:user_info:{user_id}           -> UserInfo JSON
      perm:accessible_gateways:{user_id} -> [gateway_id, ...]
      perm:gateway_perm:{role_id}        -> [{gateway_id, can_*}, ...]

    策略:
      读: 先查缓存 -> 命中返回 -> 未命中查DB并写入缓存
      写: 先写DB -> 再失效缓存
    """

    PREFIX = "perm"
    DEFAULT_TTL = 3600  # 1小时

    def __init__(self, redis: Redis):
        self.redis = redis

    # ---- key 生成 ----
    @staticmethod
    def _key_user_info(user_id: int) -> str:
        return f"perm:user_info:{user_id}"

    @staticmethod
    def _key_accessible_gateways(user_id: int) -> str:
        return f"perm:accessible_gateways:{user_id}"

    @staticmethod
    def _key_gateway_perm(role_id: int) -> str:
        return f"perm:gateway_perm:{role_id}"

    # ---- 通用读写 ----
    async def _get_json(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        if data is not None:
            return json.loads(data)
        return None

    async def _set_json(self, key: str, value: Any, ttl: int = None) -> None:
        await self.redis.set(key, json.dumps(value, default=str), ex=ttl or self.DEFAULT_TTL)

    # ---- UserInfo 缓存 ----
    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        return await self._get_json(self._key_user_info(user_id))

    async def set_user_info(self, user_id: int, user_info_dict: Dict) -> None:
        await self._set_json(self._key_user_info(user_id), user_info_dict)

    async def invalidate_user_info(self, user_id: int) -> None:
        await self.redis.delete(self._key_user_info(user_id))

    # ---- 可访问网关 缓存 ----
    async def get_accessible_gateways(self, user_id: int) -> Optional[List[str]]:
        return await self._get_json(self._key_accessible_gateways(user_id))

    async def set_accessible_gateways(self, user_id: int, gateway_ids: List[str]) -> None:
        await self._set_json(self._key_accessible_gateways(user_id), gateway_ids)

    async def invalidate_accessible_gateways(self, user_id: int) -> None:
        await self.redis.delete(self._key_accessible_gateways(user_id))

    # ---- 角色网关权限 缓存 ----
    async def get_gateway_perms_by_role(self, role_id: int) -> Optional[List[Dict]]:
        return await self._get_json(self._key_gateway_perm(role_id))

    async def set_gateway_perms_by_role(self, role_id: int, perms: List[Dict]) -> None:
        await self._set_json(self._key_gateway_perm(role_id), perms)

    async def invalidate_gateway_perms_by_role(self, role_id: int) -> None:
        await self.redis.delete(self._key_gateway_perm(role_id))

    # ---- 批量失效 ----
    async def invalidate_role_related(self, role_id: int) -> None:
        """角色权限变更时，失效该角色的缓存 + 所有用户的可访问网关缓存"""
        await self.invalidate_gateway_perms_by_role(role_id)
        keys = await self.redis.keys("perm:accessible_gateways:*")
        if keys:
            await self.redis.delete(*keys)

    async def invalidate_all_user_caches(self) -> None:
        """失效所有用户相关缓存"""
        for pattern in ["perm:user_info:*", "perm:accessible_gateways:*", "perm:gateway_perm:*"]:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
