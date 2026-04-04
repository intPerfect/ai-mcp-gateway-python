"""
Authentication service for MCP Gateway
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import AuthRepository
from app.infrastructure.database.models import McpGatewayAuth
from app.domain.auth.models import (
    LicenseCommand,
    RateLimitCommand,
    RegisterCommand,
    AuthInfo,
)
from app.utils.exceptions import AuthException, RateLimitException
from app.utils.security import (
    generate_api_key,
    hash_password,
    verify_password,
    parse_api_key,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and authorization service"""

    def __init__(self, session: AsyncSession):
        self.repository = AuthRepository(session)
        self._rate_limit_cache: dict = {}

    async def validate_license(self, command: LicenseCommand) -> bool:
        """
        Validate API key license
        """
        if not command.api_key:
            raise AuthException("API key is required")

        key_id = parse_api_key(command.api_key)
        if not key_id:
            raise AuthException("Invalid API key format")

        auth_info = await self.repository.get_gateway_auth_by_key_id(
            command.gateway_id, key_id
        )

        if auth_info is None:
            raise AuthException("Invalid or expired API key")

        if not verify_password(command.api_key, auth_info.api_key_hash):
            raise AuthException("Invalid API key")

        logger.info(f"License validated for gateway {command.gateway_id}")
        return True

    async def check_rate_limit(self, command: RateLimitCommand) -> bool:
        """
        Check if request is within rate limit
        """
        key_id = parse_api_key(command.api_key)
        if not key_id:
            raise AuthException("Invalid API key format")

        auth_info = await self.repository.get_gateway_auth_by_key_id(
            command.gateway_id, key_id
        )

        if auth_info is None:
            raise AuthException("Invalid API key")

        if not verify_password(command.api_key, auth_info.api_key_hash):
            raise AuthException("Invalid API key")

        cache_key = f"{command.gateway_id}:{key_id}"
        current_hour = datetime.now().strftime("%Y%m%d%H")
        rate_key = f"{cache_key}:{current_hour}"

        current_count = self._rate_limit_cache.get(rate_key, 0)

        if current_count >= auth_info.rate_limit:
            raise RateLimitException(
                f"Rate limit exceeded: {current_count}/{auth_info.rate_limit} requests per hour"
            )

        self._rate_limit_cache[rate_key] = current_count + 1

        old_keys = [k for k in self._rate_limit_cache.keys() if current_hour not in k]
        for k in old_keys:
            del self._rate_limit_cache[k]

        return True

    async def register_api_key(self, command: RegisterCommand) -> str:
        """
        Register a new API key for gateway
        """
        key_id, api_key = generate_api_key()
        api_key_hash = hash_password(api_key)

        expire_time = datetime.now() + timedelta(days=command.expire_days)

        auth = McpGatewayAuth(
            gateway_id=command.gateway_id,
            key_id=key_id,
            api_key_hash=api_key_hash,
            rate_limit=command.rate_limit,
            expire_time=expire_time,
            status=1,
        )

        await self.repository.insert_gateway_auth(auth)

        logger.info(f"Registered new API key for gateway {command.gateway_id}")
        return api_key

    async def get_auth_info(self, gateway_id: str, api_key: str) -> Optional[AuthInfo]:
        """Get authentication information"""
        key_id = parse_api_key(api_key)
        if not key_id:
            return None

        auth = await self.repository.get_gateway_auth_by_key_id(gateway_id, key_id)

        if auth is None:
            return None

        if not verify_password(api_key, auth.api_key_hash):
            return None

        return AuthInfo(
            gateway_id=auth.gateway_id,
            api_key=api_key,
            rate_limit=auth.rate_limit,
            expire_time=auth.expire_time,
            status=auth.status,
        )
