"""
Session domain models v3.0
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import asyncio


@dataclass
class SessionConfig:
    """会话配置"""
    session_id: str
    gateway_id: str
    api_key: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    def update_last_accessed(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.now()
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """检查会话是否过期"""
        elapsed = (datetime.now() - self.last_accessed).total_seconds() / 60
        return elapsed > timeout_minutes
    
    def mark_inactive(self):
        """标记会话为非活跃"""
        self.is_active = False


@dataclass
class HandleMessageCommand:
    """消息处理命令"""
    gateway_id: str
    api_key: str
    session_id: str
    message_body: str


@dataclass
class GatewayConfig:
    """网关配置"""
    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str]
    version: Optional[str]


@dataclass
class ToolConfig:
    """工具配置"""
    gateway_id: str
    tool_id: int
    tool_name: str
    tool_description: str
    tool_version: str
    protocol_id: int
    protocol_type: str


@dataclass
class ProtocolMapping:
    """
    协议参数映射
    
    param_location 参数位置:
    - path: 路径参数，替换URL中的{param}
    - query: 查询参数
    - body: JSON请求体参数
    - form: 表单参数
    - header: HTTP头部参数
    - file: 文件上传参数
    """
    param_location: str  # path/query/body/form/header/file
    field_name: str
    field_type: str
    field_desc: str
    is_required: int
    default_value: Optional[str] = None
    enum_values: Optional[str] = None
    example_value: Optional[str] = None
    sort_order: int = 0


@dataclass
class HttpConfig:
    """HTTP协议配置"""
    http_url: str
    http_method: str
    http_headers: Optional[str]
    timeout: int


@dataclass
class ToolProtocolConfig:
    """工具协议配置"""
    http_config: Optional[HttpConfig] = None
    mappings: List[ProtocolMapping] = field(default_factory=list)