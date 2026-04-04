# -*- coding: utf-8 -*-
"""
Redis Client - Redis connection management
"""

import logging
from typing import Optional
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
