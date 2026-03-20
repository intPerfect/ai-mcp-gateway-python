# -*- coding: utf-8 -*-
"""
OpenAPI Import API - OpenAPI规范导入功能
解析OpenAPI规范并生成MCP工具配置写入数据库
"""
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.infrastructure.database import get_db_session
from app.infrastructure.models import McpGatewayTool, McpProtocolHttp, McpProtocolMapping
from app.infrastructure.repository import McpGatewayRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class OpenAPIImportRequest(BaseModel):
    """OpenAPI导入请求"""
    gateway_id: str = "gateway_001"
    service_name: str
    service_url: str
    openapi_url: Optional[str] = None  # OpenAPI规范URL
    openapi_spec: Optional[Dict] = None  # 或者直接传入OpenAPI JSON


class OpenAPIToolInfo(BaseModel):
    """解析后的工具信息"""
    name: str
    description: str
    method: str
    path: str
    parameters: List[Dict]


async def fetch_openapi_spec(url: str) -> Dict:
    """从URL获取OpenAPI规范"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def parse_openapi_spec(spec: Dict) -> List[OpenAPIToolInfo]:
    """解析OpenAPI规范，提取工具信息"""
    tools = []
    
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue
            
            # 获取操作ID或生成
            operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
            
            # 清理名称，只保留字母数字下划线
            tool_name = "".join(c if c.isalnum() or c == '_' else '_' for c in operation_id)
            tool_name = tool_name.strip('_')
            
            # 获取描述
            description = operation.get("summary") or operation.get("description", "")
            
            # 获取参数
            parameters = []
            for param in operation.get("parameters", []):
                param_info = {
                    "name": param.get("name"),
                    "in": param.get("in"),  # query, path, header
                    "type": param.get("schema", {}).get("type", "string"),
                    "required": param.get("required", False),
                    "description": param.get("description", "")
                }
                parameters.append(param_info)
            
            # 请求体
            request_body = operation.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                if "application/json" in content:
                    json_schema = content["application/json"].get("schema", {})
                    _extract_schema_properties(json_schema, "", parameters)
            
            tools.append(OpenAPIToolInfo(
                name=tool_name,
                description=description,
                method=method.upper(),
                path=path,
                parameters=parameters
            ))
    
    return tools


def _extract_schema_properties(schema: Dict, prefix: str, params: List[Dict]):
    """递归提取schema属性"""
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        for prop_name, prop_schema in properties.items():
            full_name = f"{prefix}{prop_name}" if prefix else prop_name
            if prop_schema.get("type") == "object":
                _extract_schema_properties(prop_schema, f"{full_name}.", params)
            else:
                params.append({
                    "name": full_name,
                    "in": "body",
                    "type": prop_schema.get("type", "string"),
                    "required": prop_name in required_fields,
                    "description": prop_schema.get("description", "")
                })


def build_input_schema(parameters: List[Dict]) -> Dict:
    """根据参数构建input schema"""
    properties = {}
    required = []
    
    query_params = [p for p in parameters if p.get("in") in ["query", "body"]]
    
    for param in query_params:
        name = param["name"]
        properties[name] = {
            "type": param.get("type", "string"),
            "description": param.get("description", "")
        }
        if param.get("required"):
            required.append(name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required if required else None,
        "additionalProperties": False
    }


@router.post("/openapi/import")
async def import_openapi(
    request: OpenAPIImportRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    导入OpenAPI规范并生成MCP工具配置
    
    支持两种方式：
    1. 提供 openapi_url，服务将自动获取
    2. 直接提供 openapi_spec JSON对象
    """
    try:
        # 获取OpenAPI规范
        if request.openapi_url:
            spec = await fetch_openapi_spec(request.openapi_url)
        elif request.openapi_spec:
            spec = request.openapi_spec
        else:
            raise HTTPException(status_code=400, detail="必须提供 openapi_url 或 openapi_spec")
        
        # 解析规范
        tools = parse_openapi_spec(spec)
        
        if not tools:
            return {"code": "0000", "info": "success", "data": {
                "message": "未发现可导入的API",
                "tools": []
            }}
        
        # 写入数据库
        imported = []
        repository = McpGatewayRepository(db)
        
        for tool in tools:
            try:
                # 检查是否已存在
                existing = await repository.get_tool_by_name(request.gateway_id, tool.name)
                if existing:
                    logger.info(f"工具已存在，跳过: {tool.name}")
                    continue
                
                # 创建HTTP协议配置
                http_config = McpProtocolHttp(
                    protocol_id=0,  # 稍后更新
                    http_url=f"{request.service_url.rstrip('/')}{tool.path}",
                    http_method=tool.method,
                    http_headers=None,
                    timeout=30000,
                    status=1
                )
                db.add(http_config)
                await db.flush()
                
                protocol_id = http_config.id
                
                # 创建工具配置
                tool_config = McpGatewayTool(
                    gateway_id=request.gateway_id,
                    tool_id=http_config.id,
                    tool_name=tool.name,
                    tool_type="function",
                    tool_description=tool.description,
                    tool_version="1.0.0",
                    protocol_id=protocol_id,
                    protocol_type="http"
                )
                db.add(tool_config)
                
                # 创建参数映射
                input_schema = build_input_schema(tool.parameters)
                for idx, (param_name, param_spec) in enumerate(input_schema.get("properties", {}).items()):
                    mapping = McpProtocolMapping(
                        protocol_id=protocol_id,
                        mapping_type="request",
                        parent_path=None,
                        field_name=param_name,
                        mcp_path=param_name,
                        mcp_type=param_spec.get("type", "string"),
                        mcp_desc=param_spec.get("description", ""),
                        is_required=1 if param_name in (input_schema.get("required") or []) else 0,
                        sort_order=idx
                    )
                    db.add(mapping)
                
                imported.append({
                    "name": tool.name,
                    "description": tool.description,
                    "method": tool.method,
                    "path": tool.path
                })
                
            except Exception as e:
                logger.error(f"导入工具失败: {tool.name} - {str(e)}")
        
        await db.commit()
        
        return {
            "code": "0000",
            "info": "success",
            "data": {
                "message": f"成功导入 {len(imported)} 个工具",
                "tools": imported
            }
        }
        
    except httpx.HTTPError as e:
        logger.error(f"获取OpenAPI规范失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取OpenAPI规范失败: {str(e)}")
    except Exception as e:
        logger.error(f"导入OpenAPI失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openapi/preview")
async def preview_openapi(
    openapi_url: str,
    service_url: str
):
    """
    预览OpenAPI规范解析结果，不写入数据库
    """
    try:
        spec = await fetch_openapi_spec(openapi_url)
        tools = parse_openapi_spec(spec)
        
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
        
        return {
            "code": "0000",
            "info": "success",
            "data": {
                "total": len(preview),
                "tools": preview
            }
        }
        
    except httpx.HTTPError as e:
        logger.error(f"获取OpenAPI规范失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取OpenAPI规范失败: {str(e)}")
    except Exception as e:
        logger.error(f"预览OpenAPI失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
