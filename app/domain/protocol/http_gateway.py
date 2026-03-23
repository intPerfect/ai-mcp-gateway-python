"""
HTTP Gateway for calling external services v3.0
"""
import json
import re
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.domain.session.models import HttpConfig, ProtocolMapping

logger = logging.getLogger(__name__)


class HttpGateway:
    """HTTP网关，支持多参数位置"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def call(
        self, 
        http_config: HttpConfig, 
        arguments: Dict[str, Any],
        mappings: List[ProtocolMapping] = None
    ) -> str:
        """
        调用外部HTTP服务
        
        Args:
            http_config: HTTP协议配置
            arguments: 请求参数
            mappings: 参数映射配置（可选）
            
        Returns:
            响应文本
        """
        client = await self._get_client()
        
        # 解析headers
        headers = {}
        if http_config.http_headers:
            try:
                headers = json.loads(http_config.http_headers)
            except json.JSONDecodeError:
                logger.warning("解析HTTP headers失败")
        
        method = http_config.http_method.lower()
        url = http_config.http_url
        timeout = http_config.timeout / 1000.0
        
        # 如果有映射配置，按参数位置分发
        if mappings:
            return await self._call_with_mappings(client, method, url, headers, timeout, arguments, mappings)
        
        # 无映射配置，使用默认逻辑
        return await self._call_default(client, method, url, headers, timeout, arguments)
    
    async def _call_with_mappings(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Dict,
        timeout: float,
        arguments: Dict[str, Any],
        mappings: List[ProtocolMapping]
    ) -> str:
        """根据参数映射配置构建请求"""
        
        # 按参数位置分组
        path_params = {}
        query_params = {}
        body_params = {}
        form_params = {}
        header_params = {}
        
        for mapping in mappings:
            field_name = mapping.field_name
            value = arguments.get(field_name)
            
            if value is None:
                if mapping.default_value:
                    value = mapping.default_value
                elif mapping.is_required == 1:
                    logger.warning(f"必填参数缺失: {field_name}")
                continue
            
            location = mapping.param_location
            
            if location == "path":
                path_params[field_name] = value
            elif location == "query":
                query_params[field_name] = value
            elif location == "body":
                body_params[field_name] = value
            elif location == "form":
                form_params[field_name] = value
            elif location == "header":
                header_params[field_name] = value
        
        # 替换URL中的路径参数
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))
        
        # 添加header参数
        headers.update(header_params)
        
        logger.info(f"调用 {method.upper()} {url}")
        
        try:
            if method == "get":
                response = await client.get(
                    url,
                    headers=headers,
                    params=query_params if query_params else None,
                    timeout=timeout
                )
            elif method == "post":
                # 优先使用body参数，其次使用form参数
                if body_params:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=body_params,
                        params=query_params if query_params else None,
                        timeout=timeout
                    )
                elif form_params:
                    response = await client.post(
                        url,
                        headers=headers,
                        data=form_params,
                        params=query_params if query_params else None,
                        timeout=timeout
                    )
                else:
                    response = await client.post(
                        url,
                        headers=headers,
                        params=query_params if query_params else None,
                        timeout=timeout
                    )
            elif method == "put":
                response = await client.put(
                    url,
                    headers=headers,
                    json=body_params if body_params else None,
                    params=query_params if query_params else None,
                    timeout=timeout
                )
            elif method == "delete":
                response = await client.delete(
                    url,
                    headers=headers,
                    params=query_params if query_params else None,
                    timeout=timeout
                )
            elif method == "patch":
                response = await client.patch(
                    url,
                    headers=headers,
                    json=body_params if body_params else None,
                    params=query_params if query_params else None,
                    timeout=timeout
                )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": True,
                "status_code": e.response.status_code,
                "message": e.response.text
            })
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })
    
    async def _call_default(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Dict,
        timeout: float,
        arguments: Dict[str, Any]
    ) -> str:
        """默认调用逻辑（无映射配置时）"""
        
        # 提取请求体
        request_body = None
        if arguments:
            values = list(arguments.values())
            if values:
                request_body = values[0]
        
        logger.info(f"调用 {method.upper()} {url}")
        
        try:
            if method == "post":
                response = await client.post(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=timeout
                )
            elif method == "get":
                query_params = {}
                if request_body and isinstance(request_body, dict):
                    query_params = dict(request_body)
                    
                    # 替换路径参数
                    path_param_pattern = re.compile(r'\{([^}]+)\}')
                    for match in path_param_pattern.finditer(url):
                        param_name = match.group(1)
                        if param_name in query_params:
                            url = url.replace(f"{{{param_name}}}", str(query_params.pop(param_name)))
                
                response = await client.get(
                    url,
                    headers=headers,
                    params=query_params,
                    timeout=timeout
                )
            elif method == "put":
                response = await client.put(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=timeout
                )
            elif method == "delete":
                response = await client.delete(
                    url,
                    headers=headers,
                    timeout=timeout
                )
            elif method == "patch":
                response = await client.patch(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=timeout
                )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": True,
                "status_code": e.response.status_code,
                "message": e.response.text
            })
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })