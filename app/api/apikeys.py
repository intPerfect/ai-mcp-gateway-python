# -*- coding: utf-8 -*-
"""
API Key Management API - API Key管理接口
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter
from app.infrastructure.database import async_session_factory
from app.infrastructure.database.models import McpGatewayAuth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/apikeys")
async def get_api_keys() -> Dict[str, Any]:
    """
    获取所有API Key信息
    """
    try:
        async with async_session_factory() as session:
            from sqlalchemy import select
            # 查询网关认证信息
            result = await session.execute(
                select(McpGatewayAuth).where(McpGatewayAuth.status == 1)
            )
            auth_records = result.scalars().all()
            
            gateway_keys = []
            for auth in auth_records:
                gateway_keys.append({
                    "gateway_id": auth.gateway_id,
                    "api_key": auth.api_key,
                    "status": auth.status,
                    "expire_time": str(auth.expire_time) if auth.expire_time else None
                })
            
            # 如果没有数据，返回默认测试Key
            if not gateway_keys:
                gateway_keys.append({
                    "gateway_id": "gateway_001",
                    "api_key": "gw-test-api-key-001",
                    "status": 1,
                    "expire_time": "2099-12-31 23:59:59"
                })
            
            return {
                "code": "0000",
                "info": "success",
                "data": {
                    "gateway_keys": gateway_keys,
                    "user_keys": []
                }
            }
    except Exception as e:
        logger.error(f"获取API Keys失败: {str(e)}")
        return {
            "code": "SYSTEM_ERROR",
            "info": str(e),
            "data": {"gateway_keys": [], "user_keys": []}
        }
