# -*- coding: utf-8 -*-
"""
Cache infrastructure module
"""

from app.infrastructure.cache.redis_client import get_redis, RedisClient

__all__ = ["get_redis", "RedisClient"]
