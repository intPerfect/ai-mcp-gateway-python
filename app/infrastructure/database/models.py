# -*- coding: utf-8 -*-
"""
Database Models - ORM模型
SQLAlchemy ORM Models for MCP Gateway
"""

from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, SmallInteger, DateTime

from app.infrastructure.database.connection import Base


class McpMicroservice(Base):
    """MCP微服务配置"""

    __tablename__ = "mcp_microservice"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    http_base_url = Column(String(512), nullable=False)
    description = Column(String(512), nullable=True)
    business_line_id = Column(BigInteger, nullable=True)  # 所属业务线ID
    health_status = Column(String(16), default="unknown")
    last_check_time = Column(DateTime, nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGateway(Base):
    """MCP网关配置"""

    __tablename__ = "mcp_gateway"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), unique=True, nullable=False)
    gateway_name = Column(String(128), nullable=False)
    gateway_desc = Column(String(512), nullable=True)
    version = Column(String(16), default="1.0.0")
    business_line_id = Column(BigInteger, nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGatewayAuth(Base):
    """MCP网关认证配置"""

    __tablename__ = "mcp_gateway_auth"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)
    key_id = Column(
        String(32), unique=True, nullable=False
    )  # API Key 唯一标识，用于索引查询
    api_key_hash = Column(String(128), nullable=False)  # bcrypt 加盐哈希后的 API Key
    key_preview = Column(String(32), nullable=True)  # Key前缀预览（脱敏显示）
    rate_limit = Column(Integer, default=600)
    expire_time = Column(DateTime, nullable=True)
    remark = Column(String(256), nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGatewayMicroservice(Base):
    """网关-微服务绑定关系"""

    __tablename__ = "mcp_gateway_microservice"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)
    microservice_id = Column(BigInteger, nullable=False)
    bind_time = Column(DateTime, default=datetime.now)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpLlmConfig(Base):
    """LLM配置(统一)"""

    __tablename__ = "mcp_llm_config"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_id = Column(String(64), unique=True, nullable=False)  # 配置唯一标识
    config_name = Column(String(128), nullable=False)  # 配置名称(自定义)
    api_type = Column(String(16), nullable=False)  # API类型: openai/anthropic
    base_url = Column(String(512), nullable=False)  # API基础URL
    model_name = Column(String(128), nullable=False)  # 模型名称
    api_key = Column(Text, nullable=False)  # API Key
    description = Column(String(512), nullable=True)  # 描述
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGatewayLlm(Base):
    """网关-LLM绑定关系"""

    __tablename__ = "mcp_gateway_llm"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)  # 网关ID
    llm_config_id = Column(String(64), nullable=False)  # LLM配置ID
    bind_time = Column(DateTime, default=datetime.now)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGatewayTool(Base):
    """MCP工具配置"""

    __tablename__ = "mcp_gateway_tool"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)
    tool_id = Column(BigInteger, unique=True, nullable=False)
    tool_name = Column(String(128), nullable=False)
    tool_type = Column(String(32), nullable=False, default="function")
    tool_description = Column(String(512), nullable=False)
    tool_version = Column(String(16), nullable=False, default="1.0.0")
    protocol_id = Column(BigInteger, nullable=False)
    protocol_type = Column(String(16), nullable=False, default="http")
    microservice_id = Column(BigInteger, nullable=True)
    enabled = Column(SmallInteger, nullable=False, default=1)
    call_status = Column(String(16), default="sunny")
    last_call_time = Column(DateTime, nullable=True)
    last_call_code = Column(String(32), nullable=True)
    call_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpProtocolHttp(Base):
    """HTTP协议配置"""

    __tablename__ = "mcp_protocol_http"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    protocol_id = Column(BigInteger, unique=True, nullable=False)
    http_url = Column(String(512), nullable=False)
    http_method = Column(String(16), nullable=False, default="POST")
    http_headers = Column(Text, nullable=True)
    timeout = Column(Integer, default=30000)
    retry_times = Column(SmallInteger, default=0)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpProtocolMapping(Base):
    """
    MCP参数映射配置

    param_location 参数位置:
    - path: 路径参数，替换URL中的{param}
    - query: 查询参数，添加到URL查询字符串
    - body: JSON请求体参数
    - form: 表单参数
    - header: HTTP头部参数
    - file: 文件上传参数
    """

    __tablename__ = "mcp_protocol_mapping"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    protocol_id = Column(BigInteger, nullable=False)
    param_location = Column(
        String(16), nullable=False
    )  # path/query/body/form/header/file
    field_name = Column(String(128), nullable=False)
    field_type = Column(String(32), nullable=False, default="string")
    field_desc = Column(String(256), nullable=False)
    is_required = Column(SmallInteger, nullable=False, default=0)
    default_value = Column(String(256), nullable=True)
    enum_values = Column(String(512), nullable=True)  # JSON数组
    example_value = Column(String(256), nullable=True)
    sort_order = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============================================
# RBAC 权限系统模型
# ============================================


class SysBusinessLine(Base):
    """业务线表"""

    __tablename__ = "sys_business_line"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    line_code = Column(String(64), unique=True, nullable=False)
    line_name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysUserBusinessLine(Base):
    """用户-业务线关联表"""

    __tablename__ = "sys_user_business_line"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    business_line_id = Column(BigInteger, nullable=False)
    is_admin = Column(SmallInteger, default=0)  # 是否该业务线管理员
    create_time = Column(DateTime, default=datetime.now)


class SysUser(Base):
    """用户表"""

    __tablename__ = "sys_user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    real_name = Column(String(64), nullable=True)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    avatar = Column(String(256), nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    last_login_time = Column(DateTime, nullable=True)
    last_login_ip = Column(String(64), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysRole(Base):
    """角色表"""

    __tablename__ = "sys_role"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_code = Column(String(64), unique=True, nullable=False)
    role_name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)
    business_line_id = Column(
        BigInteger, nullable=True
    )  # 所属业务线ID，NULL表示全局角色
    is_system = Column(SmallInteger, nullable=False, default=0)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysUserRole(Base):
    """用户角色关联表"""

    __tablename__ = "sys_user_role"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, nullable=False)
    create_time = Column(DateTime, default=datetime.now)


class SysResource(Base):
    """资源表"""

    __tablename__ = "sys_resource"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    resource_code = Column(String(128), unique=True, nullable=False)
    resource_name = Column(String(128), nullable=False)
    resource_type = Column(String(32), default="menu")
    parent_id = Column(BigInteger, default=0)
    api_path = Column(String(256), nullable=True)
    icon = Column(String(64), nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysPermission(Base):
    """权限表"""

    __tablename__ = "sys_permission"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    permission_code = Column(String(128), unique=True, nullable=False)
    permission_name = Column(String(128), nullable=False)
    resource_id = Column(BigInteger, nullable=False)
    action = Column(String(32), nullable=False)
    description = Column(String(512), nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysRolePermission(Base):
    """角色权限关联表"""

    __tablename__ = "sys_role_permission"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_id = Column(BigInteger, nullable=False)
    permission_id = Column(BigInteger, nullable=False)
    create_time = Column(DateTime, default=datetime.now)


class SysGatewayPermission(Base):
    """网关权限配置"""

    __tablename__ = "sys_gateway_permission"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_id = Column(BigInteger, nullable=False)
    gateway_id = Column(String(64), nullable=False)
    can_create = Column(SmallInteger, default=0)
    can_read = Column(SmallInteger, default=0)
    can_update = Column(SmallInteger, default=0)
    can_delete = Column(SmallInteger, default=0)
    can_chat = Column(SmallInteger, default=0)
    create_time = Column(DateTime, default=datetime.now)


class SysLoginLog(Base):
    """登录日志表"""

    __tablename__ = "sys_login_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True)
    username = Column(String(64), nullable=True)
    login_ip = Column(String(64), nullable=True)
    login_time = Column(DateTime, default=datetime.now)
    login_status = Column(SmallInteger, default=1)
    fail_reason = Column(String(256), nullable=True)


class McpUsageLog(Base):
    """模型调用使用记录表"""

    __tablename__ = "mcp_usage_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)
    key_id = Column(String(32), nullable=False)
    session_id = Column(String(64), nullable=True)
    call_type = Column(String(16), nullable=False)
    call_detail = Column(String(256), nullable=True)
    call_time = Column(DateTime, default=datetime.now)
    success = Column(SmallInteger, default=1)
