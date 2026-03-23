# -*- coding: utf-8 -*-
"""
Gateway Router - 网关管理路由
包含：网关配置、网关Key、LLM配置、LLM Key 四个模块
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.database.models import (
    McpGateway, McpGatewayAuth, McpLlm, McpLlmKey
)
from app.infrastructure.database import McpGatewayRepository
from app.utils.result import Result
from app.utils.security import generate_api_key, hash_password

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Pydantic Schemas
# ============================================

class GatewayCreate(BaseModel):
    gateway_id: str
    gateway_name: str
    gateway_desc: Optional[str] = None
    version: str = "1.0.0"
    auth: int = 0


class GatewayUpdate(BaseModel):
    gateway_name: Optional[str] = None
    gateway_desc: Optional[str] = None
    version: Optional[str] = None
    auth: Optional[int] = None
    status: Optional[int] = None


class GatewayKeyCreate(BaseModel):
    gateway_id: str
    rate_limit: int = 1000
    expire_days: int = 365
    remark: Optional[str] = None


class LlmCreate(BaseModel):
    llm_id: str
    llm_name: str
    llm_type: str
    base_url: str
    default_model: Optional[str] = None
    description: Optional[str] = None


class LlmUpdate(BaseModel):
    llm_name: Optional[str] = None
    llm_type: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class LlmKeyCreate(BaseModel):
    llm_id: str
    rate_limit: int = 1000
    expire_days: int = 365
    remark: Optional[str] = None


# ============================================
# 网关配置 API
# ============================================

@router.get("/gateways")
async def get_gateways(db: AsyncSession = Depends(get_db_session)):
    """获取网关列表"""
    try:
        repository = McpGatewayRepository(db)
        gateways = await repository.get_all_gateways()
        
        data = [
            {
                "id": g.id,
                "gateway_id": g.gateway_id,
                "gateway_name": g.gateway_name,
                "gateway_desc": g.gateway_desc,
                "version": g.version,
                "auth": g.auth,
                "status": g.status,
                "create_time": str(g.create_time) if g.create_time else None,
            }
            for g in gateways
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取网关列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/gateways")
async def create_gateway(
    form: GatewayCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建网关"""
    try:
        repository = McpGatewayRepository(db)
        
        # 检查gateway_id是否已存在
        existing = await repository.get_gateway_by_id(form.gateway_id)
        if existing:
            return Result.error("DUPLICATE_ID", "网关ID已存在")
        
        gateway = McpGateway(
            gateway_id=form.gateway_id,
            gateway_name=form.gateway_name,
            gateway_desc=form.gateway_desc,
            version=form.version,
            auth=form.auth,
            status=1
        )
        
        result = await repository.create_gateway(gateway)
        return Result.success({
            "id": result.id,
            "gateway_id": result.gateway_id,
            "gateway_name": result.gateway_name
        })
    except Exception as e:
        logger.error(f"创建网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.put("/gateways/{gateway_id}")
async def update_gateway(
    gateway_id: int,
    form: GatewayUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新网关"""
    try:
        repository = McpGatewayRepository(db)
        
        update_data = {k: v for k, v in form.model_dump().items() if v is not None}
        if not update_data:
            return Result.error("INVALID_PARAM", "无更新数据")
        
        result = await repository.update_gateway(gateway_id, **update_data)
        if not result:
            return Result.error("NOT_FOUND", "网关不存在")
        
        return Result.success({"id": gateway_id})
    except Exception as e:
        logger.error(f"更新网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/gateways/{gateway_id}")
async def delete_gateway(
    gateway_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除网关"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_gateway(gateway_id)
        
        if not success:
            return Result.error("NOT_FOUND", "网关不存在")
        
        return Result.success({"id": gateway_id})
    except Exception as e:
        logger.error(f"删除网关失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# 网关Key API
# ============================================

@router.get("/gateway-keys")
async def get_gateway_keys(db: AsyncSession = Depends(get_db_session)):
    """获取网关Key列表（脱敏）"""
    try:
        repository = McpGatewayRepository(db)
        keys = await repository.get_all_gateway_keys()
        
        data = [
            {
                "id": k.id,
                "gateway_id": k.gateway_id,
                "key_id": k.key_id,
                "key_preview": k.key_preview or f"sk-{k.key_id[:8]}...",
                "rate_limit": k.rate_limit,
                "expire_time": str(k.expire_time) if k.expire_time else None,
                "remark": k.remark,
                "status": k.status,
                "create_time": str(k.create_time) if k.create_time else None,
            }
            for k in keys
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取网关Key列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/gateway-keys")
async def create_gateway_key(
    form: GatewayKeyCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建网关Key（返回完整Key，仅此一次）"""
    try:
        repository = McpGatewayRepository(db)
        
        # 生成 API Key
        key_id, full_api_key = generate_api_key()
        api_key_hash = hash_password(full_api_key)
        key_preview = f"sk-{key_id[:8]}...{full_api_key[-4:]}"
        
        expire_time = datetime.now() + timedelta(days=form.expire_days)
        
        auth = McpGatewayAuth(
            gateway_id=form.gateway_id,
            key_id=key_id,
            api_key_hash=api_key_hash,
            key_preview=key_preview,
            rate_limit=form.rate_limit,
            expire_time=expire_time,
            remark=form.remark,
            status=1
        )
        
        await repository.create_gateway_key(auth)
        
        logger.info(f"创建网关Key成功: gateway_id={form.gateway_id}, key_id={key_id}")
        
        return Result.success({
            "id": auth.id,
            "gateway_id": form.gateway_id,
            "api_key": full_api_key,  # 完整Key仅在创建时返回
            "key_preview": key_preview,
            "expire_time": expire_time.isoformat(),
            "message": "请立即保存API Key，关闭后将无法再次查看完整Key"
        })
    except Exception as e:
        logger.error(f"创建网关Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/gateway-keys/{key_id}")
async def delete_gateway_key(
    key_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除网关Key"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_gateway_key(key_id)
        
        if not success:
            return Result.error("NOT_FOUND", "Key不存在")
        
        return Result.success({"id": key_id})
    except Exception as e:
        logger.error(f"删除网关Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# LLM配置 API
# ============================================

@router.get("/llms")
async def get_llms(db: AsyncSession = Depends(get_db_session)):
    """获取LLM列表"""
    try:
        repository = McpGatewayRepository(db)
        llms = await repository.get_all_llms()
        
        data = [
            {
                "id": l.id,
                "llm_id": l.llm_id,
                "llm_name": l.llm_name,
                "llm_type": l.llm_type,
                "base_url": l.base_url,
                "default_model": l.default_model,
                "description": l.description,
                "status": l.status,
                "create_time": str(l.create_time) if l.create_time else None,
            }
            for l in llms
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取LLM列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/llms")
async def create_llm(
    form: LlmCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建LLM配置"""
    try:
        repository = McpGatewayRepository(db)
        
        # 检查llm_id是否已存在
        existing = await repository.get_llm_by_llm_id(form.llm_id)
        if existing:
            return Result.error("DUPLICATE_ID", "LLM ID已存在")
        
        llm = McpLlm(
            llm_id=form.llm_id,
            llm_name=form.llm_name,
            llm_type=form.llm_type,
            base_url=form.base_url,
            default_model=form.default_model,
            description=form.description,
            status=1
        )
        
        result = await repository.create_llm(llm)
        return Result.success({
            "id": result.id,
            "llm_id": result.llm_id,
            "llm_name": result.llm_name
        })
    except Exception as e:
        logger.error(f"创建LLM配置失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.put("/llms/{llm_id}")
async def update_llm(
    llm_id: int,
    form: LlmUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新LLM配置"""
    try:
        repository = McpGatewayRepository(db)
        
        update_data = {k: v for k, v in form.model_dump().items() if v is not None}
        if not update_data:
            return Result.error("INVALID_PARAM", "无更新数据")
        
        result = await repository.update_llm(llm_id, **update_data)
        if not result:
            return Result.error("NOT_FOUND", "LLM配置不存在")
        
        return Result.success({"id": llm_id})
    except Exception as e:
        logger.error(f"更新LLM配置失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/llms/{llm_id}")
async def delete_llm(
    llm_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除LLM配置"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_llm(llm_id)
        
        if not success:
            return Result.error("NOT_FOUND", "LLM配置不存在")
        
        return Result.success({"id": llm_id})
    except Exception as e:
        logger.error(f"删除LLM配置失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


# ============================================
# LLM Key API
# ============================================

@router.get("/llm-keys")
async def get_llm_keys(db: AsyncSession = Depends(get_db_session)):
    """获取LLM Key列表（脱敏）"""
    try:
        repository = McpGatewayRepository(db)
        keys = await repository.get_all_llm_keys()
        
        data = [
            {
                "id": k.id,
                "llm_id": k.llm_id,
                "key_id": k.key_id,
                "key_preview": k.key_preview or f"llm-{k.key_id[:8]}...",
                "rate_limit": k.rate_limit,
                "expire_time": str(k.expire_time) if k.expire_time else None,
                "remark": k.remark,
                "status": k.status,
                "create_time": str(k.create_time) if k.create_time else None,
            }
            for k in keys
        ]
        return Result.success(data)
    except Exception as e:
        logger.error(f"获取LLM Key列表失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.post("/llm-keys")
async def create_llm_key(
    form: LlmKeyCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建LLM Key（返回完整Key，仅此一次）"""
    try:
        repository = McpGatewayRepository(db)
        
        # 检查LLM是否存在
        llm = await repository.get_llm_by_llm_id(form.llm_id)
        if not llm:
            return Result.error("NOT_FOUND", "LLM配置不存在")
        
        # 生成 LLM Key
        key_id, full_key = generate_api_key()
        key_hash = hash_password(full_key)
        key_preview = f"llm-{key_id[:8]}...{full_key[-4:]}"
        
        expire_time = datetime.now() + timedelta(days=form.expire_days)
        
        llm_key = McpLlmKey(
            llm_id=form.llm_id,
            key_id=key_id,
            api_key_hash=key_hash,
            key_preview=key_preview,
            rate_limit=form.rate_limit,
            expire_time=expire_time,
            remark=form.remark,
            status=1
        )
        
        await repository.create_llm_key(llm_key)
        
        logger.info(f"创建LLM Key成功: llm_id={form.llm_id}, key_id={key_id}")
        
        return Result.success({
            "id": llm_key.id,
            "llm_id": form.llm_id,
            "llm_key": full_key,  # 完整Key仅在创建时返回
            "key_preview": key_preview,
            "expire_time": expire_time.isoformat(),
            "message": "请立即保存API Key，关闭后将无法再次查看完整Key"
        })
    except Exception as e:
        logger.error(f"创建LLM Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))


@router.delete("/llm-keys/{key_id}")
async def delete_llm_key(
    key_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除LLM Key"""
    try:
        repository = McpGatewayRepository(db)
        success = await repository.delete_llm_key(key_id)
        
        if not success:
            return Result.error("NOT_FOUND", "Key不存在")
        
        return Result.success({"id": key_id})
    except Exception as e:
        logger.error(f"删除LLM Key失败: {str(e)}")
        return Result.error("SYSTEM_ERROR", str(e))
