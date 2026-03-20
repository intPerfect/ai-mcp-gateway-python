"""
Authentication domain models
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AuthInfo:
    """Authentication information"""
    gateway_id: str
    api_key: str
    rate_limit: int
    expire_time: datetime
    status: int


@dataclass
class LicenseCommand:
    """License validation command"""
    gateway_id: str
    api_key: str


@dataclass
class RateLimitCommand:
    """Rate limit check command"""
    gateway_id: str
    api_key: str


@dataclass
class RegisterCommand:
    """API key registration command"""
    gateway_id: str
    rate_limit: int = 1000
    expire_days: int = 30
