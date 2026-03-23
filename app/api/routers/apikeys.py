# -*- coding: utf-8 -*-
"""
API Keys Router - API密钥管理路由
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import McpGatewayAuth
from app.infrastructure.database import McpGatewayRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/apikeys/create")
async def create_api_key(
    gateway_id: str = "gateway_001",
    remark: str = "",
    db: AsyncSession = Depends(get_db_session)
):
    """创建新的API Key"""
    import secrets
    from datetime import datetime, timedelta
    
    api_key = f"sk-{secrets.token_hex(16)}"
    expire_time = datetime.now() + timedelta(days=365)
    
    auth = McpGatewayAuth(
        gateway_id=gateway_id,
        api_key=api_key,
        remark=remark,
        expire_time=expire_time,
        status=1
    )
    
    repository = McpGatewayRepository(db)
    await repository.insert_gateway_auth(auth)
    
    return {
        "code": "0000",
        "info": "success",
        "data": {
            "api_key": api_key,
            "expire_time": expire_time.isoformat()
        }
    }


@router.get("/apikeys/list")
async def list_api_keys(
    gateway_id: str = "gateway_001",
    db: AsyncSession = Depends(get_db_session)
):
    """列出所有API Key"""
    repository = McpGatewayRepository(db)
    count = await repository.get_effective_auth_count(gateway_id)
    
    return {
        "code": "0000",
        "info": "success",
        "data": {
            "gateway_id": gateway_id,
            "active_count": count
        }
    }
