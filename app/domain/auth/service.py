"""
Authentication service for MCP Gateway
"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import McpGatewayRepository
from app.infrastructure.database.models import McpGatewayAuth
from app.domain.auth.models import LicenseCommand, RateLimitCommand, RegisterCommand, AuthInfo
from app.utils.exceptions import AuthException, RateLimitException

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self, session: AsyncSession):
        self.repository = McpGatewayRepository(session)
        self._rate_limit_cache: dict = {}  # Simple in-memory rate limit cache
    
    async def validate_license(self, command: LicenseCommand) -> bool:
        """
        Validate API key license
        
        Args:
            command: License validation command
            
        Returns:
            True if license is valid
            
        Raises:
            AuthException: If license validation fails
        """
        # Check if gateway requires auth
        auth_status = await self.repository.get_gateway_auth_status(command.gateway_id)
        
        if auth_status is None:
            raise AuthException(f"Gateway {command.gateway_id} not found")
        
        # If auth is disabled (0), allow access
        if auth_status == 0:
            logger.info(f"Gateway {command.gateway_id} auth is disabled, allowing access")
            return True
        
        # Auth is required, validate api_key
        if not command.api_key:
            raise AuthException("API key is required")
        
        auth_info = await self.repository.get_gateway_auth_by_api_key(
            command.gateway_id, 
            command.api_key
        )
        
        if auth_info is None:
            raise AuthException("Invalid or expired API key")
        
        logger.info(f"License validated for gateway {command.gateway_id}")
        return True
    
    async def check_rate_limit(self, command: RateLimitCommand) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            command: Rate limit check command
            
        Returns:
            True if within rate limit
            
        Raises:
            RateLimitException: If rate limit exceeded
        """
        # Get auth info
        auth_info = await self.repository.get_gateway_auth_by_api_key(
            command.gateway_id,
            command.api_key
        )
        
        if auth_info is None:
            # If no auth required, skip rate limit
            auth_status = await self.repository.get_gateway_auth_status(command.gateway_id)
            if auth_status == 0:
                return True
            raise AuthException("Invalid API key")
        
        # Simple rate limiting using in-memory cache
        cache_key = f"{command.gateway_id}:{command.api_key}"
        current_hour = datetime.now().strftime("%Y%m%d%H")
        rate_key = f"{cache_key}:{current_hour}"
        
        current_count = self._rate_limit_cache.get(rate_key, 0)
        
        if current_count >= auth_info.rate_limit:
            raise RateLimitException(
                f"Rate limit exceeded: {current_count}/{auth_info.rate_limit} requests per hour"
            )
        
        # Increment counter
        self._rate_limit_cache[rate_key] = current_count + 1
        
        # Clean old entries (simple cleanup)
        old_keys = [k for k in self._rate_limit_cache.keys() if current_hour not in k]
        for k in old_keys:
            del self._rate_limit_cache[k]
        
        return True
    
    async def register_api_key(self, command: RegisterCommand) -> str:
        """
        Register a new API key for gateway
        
        Args:
            command: Registration command
            
        Returns:
            Generated API key
        """
        # Generate secure API key
        api_key = f"gw-{secrets.token_urlsafe(36)}"
        
        # Calculate expiration
        expire_time = datetime.now() + timedelta(days=command.expire_days)
        
        # Create auth record
        auth = McpGatewayAuth(
            gateway_id=command.gateway_id,
            api_key=api_key,
            rate_limit=command.rate_limit,
            expire_time=expire_time,
            status=1
        )
        
        await self.repository.insert_gateway_auth(auth)
        
        logger.info(f"Registered new API key for gateway {command.gateway_id}")
        return api_key
    
    async def get_auth_info(self, gateway_id: str, api_key: str) -> Optional[AuthInfo]:
        """Get authentication information"""
        auth = await self.repository.get_gateway_auth_by_api_key(gateway_id, api_key)
        
        if auth is None:
            return None
        
        return AuthInfo(
            gateway_id=auth.gateway_id,
            api_key=auth.api_key,
            rate_limit=auth.rate_limit,
            expire_time=auth.expire_time,
            status=auth.status
        )
