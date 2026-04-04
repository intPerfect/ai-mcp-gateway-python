# -*- coding: utf-8 -*-
"""
OpenAPI Generator - 工具配置生成器
从解析后的OpenAPI信息生成数据库配置
"""
import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

from app.domain.protocol.openapi.parser import OpenAPIToolInfo

logger = logging.getLogger(__name__)


@dataclass
class ToolConfigResult:
    """工具配置生成结果"""
    name: str
    description: str
    method: str
    path: str
    full_url: str
    http_config: Dict[str, Any]
    tool_config: Dict[str, Any]
    param_mappings: List[Dict[str, Any]]
    param_count: int


def generate_tool_configs(
    tools: List[OpenAPIToolInfo],
    gateway_id: str,
    service_url: str
) -> List[ToolConfigResult]:
    """
    从解析后的工具信息生成数据库配置
    
    Args:
        tools: 解析后的工具信息列表
        gateway_id: 网关ID
        service_url: 服务基础URL
        
    Returns:
        工具配置结果列表
    """
    results = []
    
    for tool in tools:
        full_url = f"{service_url.rstrip('/')}{tool.path}"
        
        # HTTP协议配置
        http_config = {
            "protocol_id": 0,  # 将在数据库插入后更新
            "http_url": full_url,
            "http_method": tool.method,
            "http_headers": None,
            "timeout": 30000,
            "status": 1
        }
        
        # 工具配置
        tool_config = {
            "gateway_id": gateway_id,
            "tool_id": 0,  # 将在数据库插入后更新
            "tool_name": tool.name,
            "tool_type": "function",
            "tool_description": tool.description,
            "tool_version": "1.0.0",
            "protocol_id": 0,  # 将在数据库插入后更新
            "protocol_type": "http"
        }
        
        # 参数映射
        param_mappings = []
        for idx, param in enumerate(tool.parameters):
            param_name = param.get("name", "")
            param_in = param.get("param_in", "query")
            param_desc = param.get("description", "")
            param_type = param.get("type", "string")
            param_required = param.get("required", False)
            param_default = param.get("default")
            param_enum = param.get("enum")
            param_example = param.get("example")
            
            if param_type.startswith("array"):
                field_type = "array"
            else:
                field_type = param_type
            
            mapping = {
                "protocol_id": 0,  # 将在数据库插入后更新
                "param_location": param_in,
                "field_name": param_name,
                "field_type": field_type,
                "field_desc": param_desc,
                "is_required": 1 if param_required else 0,
                "default_value": str(param_default) if param_default is not None else None,
                "enum_values": json.dumps(param_enum) if param_enum else None,
                "example_value": str(param_example) if param_example is not None else None,
                "sort_order": idx
            }
            param_mappings.append(mapping)
        
        results.append(ToolConfigResult(
            name=tool.name,
            description=tool.description,
            method=tool.method,
            path=tool.path,
            full_url=full_url,
            http_config=http_config,
            tool_config=tool_config,
            param_mappings=param_mappings,
            param_count=len(tool.parameters)
        ))
    
    return results


def build_preview_data(
    tools: List[OpenAPIToolInfo],
    service_url: str
) -> List[Dict[str, Any]]:
    """
    构建预览数据
    
    Args:
        tools: 解析后的工具信息列表
        service_url: 服务基础URL
        
    Returns:
        预览数据列表
    """
    preview = []
    for tool in tools:
        preview.append({
            "name": tool.name,
            "description": tool.description,
            "method": tool.method,
            "path": tool.path,
            "full_url": f"{service_url.rstrip('/')}{tool.path}",
            "parameters": tool.parameters
        })
    return preview
