# -*- coding: utf-8 -*-
"""
Security Utilities - 安全工具模块
提供密码哈希、API Key 处理等安全相关功能
"""

import secrets
import bcrypt


def hash_password(password: str) -> str:
    """
    使用 bcrypt 对密码进行加盐哈希

    Args:
        password: 原始密码字符串

    Returns:
        bcrypt 哈希后的字符串（包含 salt）
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配

    Args:
        plain_password: 原始密码字符串
        hashed_password: bcrypt 哈希后的密码字符串

    Returns:
        True 如果密码匹配，否则 False
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def generate_api_key() -> tuple[str, str]:
    """
    生成安全的 API Key

    Returns:
        tuple: (key_id, full_api_key)
        - key_id: 用于数据库索引查询的短ID
        - full_api_key: 完整的 API Key（返回给用户）
    """
    # 生成唯一标识符（用于索引查询）
    key_id = secrets.token_hex(8)  # 16字符
    # 生成随机密钥部分
    key_secret = secrets.token_urlsafe(32)  # 约43字符
    # 组合成完整 API Key: sk-{key_id}:{secret}
    full_api_key = f"sk-{key_id}:{key_secret}"

    return key_id, full_api_key


def parse_api_key(api_key: str) -> str | None:
    """
    从 API Key 中提取 key_id

    Args:
        api_key: 完整的 API Key

    Returns:
        key_id 或 None（如果格式无效）
    """
    if not api_key or not api_key.startswith("sk-"):
        return None

    try:
        # 格式: sk-{key_id}:{secret}
        parts = api_key[3:].split(":", 1)
        if len(parts) == 2:
            return parts[0]
        return None
    except Exception:
        return None
