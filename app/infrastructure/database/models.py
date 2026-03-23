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
    business_line = Column(String(128), nullable=True)
    health_status = Column(String(16), default='unknown')
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
    version = Column(String(16), default='1.0.0')
    auth = Column(SmallInteger, default=0)
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class McpGatewayAuth(Base):
    """MCP网关认证配置"""
    __tablename__ = "mcp_gateway_auth"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False)
    api_key = Column(String(128), unique=True, nullable=False)
    rate_limit = Column(Integer, default=1000)
    expire_time = Column(DateTime, nullable=True)
    remark = Column(String(256), nullable=True)
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
    tool_type = Column(String(32), nullable=False, default='function')
    tool_description = Column(String(512), nullable=False)
    tool_version = Column(String(16), nullable=False, default='1.0.0')
    protocol_id = Column(BigInteger, nullable=False)
    protocol_type = Column(String(16), nullable=False, default='http')
    microservice_id = Column(BigInteger, nullable=True)
    enabled = Column(SmallInteger, nullable=False, default=1)
    call_status = Column(String(16), default='sunny')
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
    http_method = Column(String(16), nullable=False, default='POST')
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
    param_location = Column(String(16), nullable=False)  # path/query/body/form/header/file
    field_name = Column(String(128), nullable=False)
    field_type = Column(String(32), nullable=False, default='string')
    field_desc = Column(String(256), nullable=False)
    is_required = Column(SmallInteger, nullable=False, default=0)
    default_value = Column(String(256), nullable=True)
    enum_values = Column(String(512), nullable=True)  # JSON数组
    example_value = Column(String(256), nullable=True)
    sort_order = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
