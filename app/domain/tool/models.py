# -*- coding: utf-8 -*-
"""
Tool Models - 工具领域模型
"""
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None


@dataclass
class ToolStatus:
    """工具状态"""
    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    http_url: str
    error: Optional[str] = None
