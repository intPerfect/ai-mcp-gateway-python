"""
Session domain models
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncio


@dataclass
class SessionConfig:
    """Session configuration"""
    session_id: str
    gateway_id: str
    api_key: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    def update_last_accessed(self):
        """Update last accessed timestamp"""
        self.last_accessed = datetime.now()
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session is expired"""
        elapsed = (datetime.now() - self.last_accessed).total_seconds() / 60
        return elapsed > timeout_minutes
    
    def mark_inactive(self):
        """Mark session as inactive"""
        self.is_active = False


@dataclass
class HandleMessageCommand:
    """Command for handling messages"""
    gateway_id: str
    api_key: str
    session_id: str
    message_body: str


@dataclass
class GatewayConfig:
    """Gateway configuration"""
    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str]
    version: Optional[str]


@dataclass
class ToolConfig:
    """Tool configuration"""
    gateway_id: str
    tool_id: int
    tool_name: str
    tool_description: str
    tool_version: str
    protocol_id: int
    protocol_type: str


@dataclass
class ProtocolMapping:
    """Protocol mapping configuration"""
    mapping_type: str
    parent_path: Optional[str]
    field_name: str
    mcp_path: str
    mcp_type: str
    mcp_desc: Optional[str]
    is_required: int
    sort_order: int


@dataclass
class HttpConfig:
    """HTTP protocol configuration"""
    http_url: str
    http_method: str
    http_headers: Optional[str]
    timeout: int


@dataclass
class ToolProtocolConfig:
    """Tool protocol configuration"""
    http_config: Optional[HttpConfig] = None
    request_mappings: List[ProtocolMapping] = field(default_factory=list)
