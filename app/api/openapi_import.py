# -*- coding: utf-8 -*-
"""
OpenAPI Import API v3.0 - OpenAPI规范导入功能
解析OpenAPI规范并生成MCP工具配置写入数据库
支持多种HTTP传参方式：path/query/header/body/form/file
"""
import json
import logging
import re
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
    openapi_url: Optional[str] = None
    openapi_spec: Optional[Dict] = None


class OpenAPIToolInfo(BaseModel):
    """解析后的工具信息"""
    name: str
    description: str
    method: str
    path: str
    parameters: List[Dict]


class ParameterInfo(BaseModel):
    """参数信息"""
    name: str
    param_in: str  # path, query, header, body, form, file
    type: str
    required: bool
    description: str
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    example: Optional[Any] = None


async def fetch_openapi_spec(url: str) -> Dict:
    """从URL获取OpenAPI规范"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def generate_param_description(param_name: str, param_type: str, param_in: str) -> str:
    """根据参数名称生成自然语言描述"""
    common_descriptions = {
        'product_id': '商品ID', 'product_name': '商品名称', 'sku': '商品SKU编码',
        'price': '价格', 'stock': '库存数量', 'category_id': '分类ID',
        'category_name': '分类名称', 'status': '状态', 'keyword': '搜索关键词',
        'page': '页码', 'page_size': '每页数量', 'limit': '返回数量限制',
        'order_id': '订单ID', 'order_no': '订单编号', 'customer_name': '客户姓名',
        'customer_phone': '客户电话', 'shipping_address': '收货地址',
        'payment_method': '支付方式', 'quantity': '数量', 'amount': '金额',
        'total_amount': '总金额', 'discount_amount': '折扣金额',
        'remark': '备注', 'reason': '原因', 'reservation_id': '预留ID',
        'ttl_seconds': '有效期(秒)', 'threshold': '阈值', 'coupon_code': '优惠券码',
        'code': '代码/编码', 'member_level': '会员等级', 'start_date': '开始日期',
        'end_date': '结束日期', 'created_at': '创建时间', 'updated_at': '更新时间',
        'id': 'ID', 'name': '名称', 'description': '描述', 'type': '类型',
        'items': '项目列表', 'data': '数据', 'action': '操作',
    }
    
    if param_name.lower() in common_descriptions:
        return common_descriptions[param_name.lower()]
    
    snake_name = re.sub(r'([A-Z])', r'_\1', param_name).lower()
    words = snake_name.split('_')
    
    word_translations = {
        'get': '获取', 'list': '列表', 'create': '创建', 'update': '更新', 'delete': '删除',
        'add': '添加', 'remove': '移除', 'set': '设置', 'check': '检查', 'search': '搜索',
        'find': '查找', 'query': '查询', 'filter': '筛选', 'sort': '排序',
        'user': '用户', 'order': '订单', 'product': '商品', 'category': '分类',
        'item': '项目', 'detail': '详情', 'info': '信息', 'config': '配置',
        'id': 'ID', 'no': '编号', 'code': '编码', 'name': '名称', 'type': '类型',
        'status': '状态', 'time': '时间', 'date': '日期', 'count': '数量',
        'total': '总计', 'start': '开始', 'end': '结束', 'min': '最小', 'max': '最大',
        'is': '是否', 'has': '是否有', 'enable': '启用', 'disable': '禁用',
        'file': '文件', 'image': '图片', 'url': '链接', 'path': '路径',
        'email': '邮箱', 'phone': '电话', 'address': '地址', 'city': '城市',
        'country': '国家', 'province': '省份', 'district': '区县',
        'payment': '支付', 'shipping': '配送', 'delivery': '交付',
        'price': '价格', 'cost': '成本', 'amount': '金额', 'fee': '费用',
        'discount': '折扣', 'coupon': '优惠券', 'member': '会员', 'level': '等级',
        'stock': '库存', 'inventory': '库存', 'reserve': '预留',
        'tag': '标签', 'brand': '品牌', 'page': '页码', 'size': '大小',
        'limit': '限制', 'offset': '偏移量', 'asc': '升序', 'desc': '降序',
        'key': '键', 'value': '值', 'token': '令牌', 'secret': '密钥',
        'api': 'API', 'http': 'HTTP', 'method': '方法',
        'header': '头部', 'body': '主体', 'param': '参数',
        'success': '成功', 'error': '错误', 'message': '消息', 'result': '结果',
        'response': '响应', 'request': '请求',
    }
    
    translated_words = []
    for word in words:
        if word in word_translations:
            translated_words.append(word_translations[word])
        else:
            translated_words.append(word)
    
    return ''.join(translated_words) if translated_words else param_name


def resolve_schema_ref(spec: Dict, schema: Dict) -> Dict:
    """解析 $ref 引用"""
    if '$ref' in schema:
        ref_path = schema['$ref']
        if ref_path.startswith('#/'):
            parts = ref_path[2:].split('/')
            resolved = spec
            for part in parts:
                resolved = resolved.get(part, {})
            return resolved
    return schema


def extract_param_info(
    param_name: str,
    param_schema: Dict,
    param_in: str,
    required: bool,
    description: str,
    spec: Dict
) -> ParameterInfo:
    """提取参数完整信息"""
    schema = resolve_schema_ref(spec, param_schema)
    param_type = schema.get('type', 'string')
    
    if param_type == 'array':
        items = schema.get('items', {})
        items = resolve_schema_ref(spec, items)
        item_type = items.get('type', 'string')
        param_type = f'array[{item_type}]'
    
    enum_values = schema.get('enum')
    default_value = schema.get('default')
    example_value = schema.get('example')
    
    final_desc = description if description else generate_param_description(param_name, param_type, param_in)
    
    if enum_values:
        enum_str = ', '.join(str(v) for v in enum_values)
        final_desc = f"{final_desc}。可选值: {enum_str}"
    
    return ParameterInfo(
        name=param_name,
        param_in=param_in,
        type=param_type,
        required=required,
        description=final_desc,
        default=default_value,
        enum=enum_values,
        example=example_value
    )


def parse_openapi_spec(spec: Dict) -> List[OpenAPIToolInfo]:
    """解析OpenAPI规范，提取工具信息"""
    tools = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue
            
            operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
            tool_name = "".join(c if c.isalnum() or c == '_' else '_' for c in operation_id)
            tool_name = tool_name.strip('_')
            
            summary = operation.get("summary", "")
            description = operation.get("description", "")
            tool_desc = f"{summary}。{description}" if summary and description else (summary or description)
            
            parameters = []
            
            # 解析 path/query/header 参数
            for param in operation.get("parameters", []):
                param_name = param.get("name", "")
                param_in = param.get("in", "query")
                param_schema = param.get("schema", {})
                required = param.get("required", False)
                param_desc = param.get("description", "")
                
                param_info = extract_param_info(
                    param_name, param_schema, param_in, required, param_desc, spec
                )
                parameters.append(param_info.model_dump())
            
            # 解析 requestBody
            request_body = operation.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                required = request_body.get("required", False)
                
                if "application/json" in content:
                    json_content = content["application/json"]
                    schema = json_content.get("schema", {})
                    schema = resolve_schema_ref(spec, schema)
                    
                    if schema.get("type") == "object":
                        properties = schema.get("properties", {})
                        required_fields = schema.get("required", [])
                        
                        for prop_name, prop_schema in properties.items():
                            prop_schema = resolve_schema_ref(spec, prop_schema)
                            prop_desc = prop_schema.get("description", "")
                            
                            param_info = extract_param_info(
                                prop_name, prop_schema, "body",
                                prop_name in required_fields, prop_desc, spec
                            )
                            parameters.append(param_info.model_dump())
                    else:
                        body_desc = schema.get("description", "请求体")
                        param_info = extract_param_info(
                            "body", schema, "body", required, body_desc, spec
                        )
                        parameters.append(param_info.model_dump())
                
                elif "application/x-www-form-urlencoded" in content:
                    form_content = content["application/x-www-form-urlencoded"]
                    schema = form_content.get("schema", {})
                    schema = resolve_schema_ref(spec, schema)
                    
                    if schema.get("type") == "object":
                        properties = schema.get("properties", {})
                        required_fields = schema.get("required", [])
                        
                        for prop_name, prop_schema in properties.items():
                            prop_schema = resolve_schema_ref(spec, prop_schema)
                            prop_desc = prop_schema.get("description", "")
                            
                            param_info = extract_param_info(
                                prop_name, prop_schema, "form",
                                prop_name in required_fields, prop_desc, spec
                            )
                            parameters.append(param_info.model_dump())
                
                elif "multipart/form-data" in content:
                    multipart_content = content["multipart/form-data"]
                    schema = multipart_content.get("schema", {})
                    schema = resolve_schema_ref(spec, schema)
                    
                    if schema.get("type") == "object":
                        properties = schema.get("properties", {})
                        required_fields = schema.get("required", [])
                        
                        for prop_name, prop_schema in properties.items():
                            prop_schema = resolve_schema_ref(spec, prop_schema)
                            prop_desc = prop_schema.get("description", "")
                            
                            prop_type = prop_schema.get("type", "string")
                            if prop_type == "string" and prop_schema.get("format") == "binary":
                                prop_type = "file"
                            
                            param_info = ParameterInfo(
                                name=prop_name,
                                param_in="file" if prop_type == "file" else "form",
                                type=prop_type,
                                required=prop_name in required_fields,
                                description=prop_desc if prop_desc else generate_param_description(prop_name, prop_type, "form"),
                                default=prop_schema.get("default"),
                                enum=prop_schema.get("enum"),
                                example=prop_schema.get("example")
                            )
                            parameters.append(param_info.model_dump())
            
            tools.append(OpenAPIToolInfo(
                name=tool_name,
                description=tool_desc,
                method=method.upper(),
                path=path,
                parameters=parameters
            ))
    
    return tools


@router.post("/openapi/import")
async def import_openapi(
    request: OpenAPIImportRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    导入OpenAPI规范并生成MCP工具配置
    """
    try:
        if request.openapi_url:
            spec = await fetch_openapi_spec(request.openapi_url)
        elif request.openapi_spec:
            spec = request.openapi_spec
        else:
            raise HTTPException(status_code=400, detail="必须提供 openapi_url 或 openapi_spec")
        
        tools = parse_openapi_spec(spec)
        
        if not tools:
            return {"code": "0000", "info": "success", "data": {
                "message": "未发现可导入的API",
                "tools": []
            }}
        
        imported = []
        repository = McpGatewayRepository(db)
        
        for tool in tools:
            try:
                existing = await repository.get_tool_by_name(request.gateway_id, tool.name)
                if existing:
                    logger.info(f"工具已存在，跳过: {tool.name}")
                    continue
                
                # 创建HTTP协议配置
                http_config = McpProtocolHttp(
                    protocol_id=0,
                    http_url=f"{request.service_url.rstrip('/')}{tool.path}",
                    http_method=tool.method,
                    http_headers=None,
                    timeout=30000,
                    status=1
                )
                db.add(http_config)
                await db.flush()
                
                protocol_id = http_config.id
                
                # 更新protocol_id
                http_config.protocol_id = protocol_id
                
                # 创建工具配置
                tool_config = McpGatewayTool(
                    gateway_id=request.gateway_id,
                    tool_id=protocol_id,
                    tool_name=tool.name,
                    tool_type="function",
                    tool_description=tool.description,
                    tool_version="1.0.0",
                    protocol_id=protocol_id,
                    protocol_type="http"
                )
                db.add(tool_config)
                
                # 创建参数映射
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
                    
                    mapping = McpProtocolMapping(
                        protocol_id=protocol_id,
                        param_location=param_in,  # 新字段名
                        field_name=param_name,
                        field_type=field_type,
                        field_desc=param_desc,
                        is_required=1 if param_required else 0,
                        default_value=str(param_default) if param_default is not None else None,
                        enum_values=json.dumps(param_enum) if param_enum else None,
                        example_value=str(param_example) if param_example is not None else None,
                        sort_order=idx
                    )
                    db.add(mapping)
                
                imported.append({
                    "name": tool.name,
                    "description": tool.description,
                    "method": tool.method,
                    "path": tool.path,
                    "param_count": len(tool.parameters)
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
async def preview_openapi(openapi_url: str, service_url: str):
    """预览OpenAPI规范解析结果"""
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