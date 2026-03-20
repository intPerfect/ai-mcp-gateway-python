"""
HTTP Gateway for calling external services
"""
import json
import re
import logging
from typing import Any, Dict, Optional
import httpx
from app.domain.session.models import HttpConfig

logger = logging.getLogger(__name__)


class HttpGateway:
    """Gateway for making HTTP calls to external services"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def call(self, http_config: HttpConfig, arguments: Dict[str, Any]) -> str:
        """
        Call external HTTP service
        
        Args:
            http_config: HTTP protocol configuration
            arguments: Request arguments
            
        Returns:
            Response as string
        """
        client = await self._get_client()
        
        # Parse headers
        headers = {}
        if http_config.http_headers:
            try:
                headers = json.loads(http_config.http_headers)
            except json.JSONDecodeError:
                logger.warning("Failed to parse HTTP headers")
        
        method = http_config.http_method.lower()
        url = http_config.http_url
        timeout = http_config.timeout / 1000.0  # Convert to seconds
        
        # Extract the actual request body from arguments
        # Arguments typically come as {"xxxRequest01": {...}}
        request_body = None
        if arguments:
            # Get the first value if it's a wrapper object
            values = list(arguments.values())
            if values:
                request_body = values[0]
        
        logger.info(f"Calling {method.upper()} {url}")
        
        try:
            if method == "post":
                response = await client.post(
                    url,
                    headers=headers,
                    json=request_body,
                    timeout=timeout
                )
            elif method == "get":
                # Handle path parameters for GET requests
                query_params = {}
                if request_body and isinstance(request_body, dict):
                    query_params = dict(request_body)
                    
                    # Replace path parameters
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
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return json.dumps({
                "error": True,
                "status_code": e.response.status_code,
                "message": e.response.text
            })
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return json.dumps({
                "error": True,
                "message": str(e)
            })
