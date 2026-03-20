"""
SQLAlchemy ORM Models for MCP Gateway
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, SmallInteger, DateTime
from app.infrastructure.database import Base


class McpGateway(Base):
    """MCP Gateway Configuration Model"""
    __tablename__ = "mcp_gateway"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), unique=True, nullable=False, comment="Gateway unique identifier")
    gateway_name = Column(String(128), nullable=False, comment="Gateway name")
    gateway_desc = Column(String(512), nullable=True, comment="Gateway description")
    version = Column(String(16), nullable=True, comment="Gateway version")
    auth = Column(SmallInteger, default=0, comment="Auth status: 0-disabled, 1-enabled")
    status = Column(SmallInteger, nullable=False, default=1, comment="Status: 0-disabled, 1-enabled")
    create_time = Column(DateTime, default=datetime.now, comment="Create time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update time")


class McpGatewayAuth(Base):
    """MCP Gateway Auth Configuration Model"""
    __tablename__ = "mcp_gateway_auth"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False, comment="Gateway ID")
    api_key = Column(String(128), unique=True, nullable=True, comment="API key")
    rate_limit = Column(Integer, default=1000, comment="Rate limit per hour")
    expire_time = Column(DateTime, nullable=True, comment="Expiration time")
    status = Column(SmallInteger, nullable=False, default=1, comment="Status: 0-disabled, 1-enabled")
    create_time = Column(DateTime, default=datetime.now, comment="Create time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update time")


class McpGatewayTool(Base):
    """MCP Gateway Tool Model"""
    __tablename__ = "mcp_gateway_tool"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    gateway_id = Column(String(64), nullable=False, comment="Gateway ID")
    tool_id = Column(BigInteger, nullable=False, unique=True, comment="Tool ID")
    tool_name = Column(String(128), nullable=False, comment="MCP tool name")
    tool_type = Column(String(32), nullable=False, default="function", comment="Tool type")
    tool_description = Column(String(512), nullable=False, comment="Tool description")
    tool_version = Column(String(16), nullable=False, comment="Tool version")
    protocol_id = Column(BigInteger, nullable=False, comment="Protocol ID")
    protocol_type = Column(String(4), nullable=False, default="http", comment="Protocol type")
    create_time = Column(DateTime, default=datetime.now, comment="Create time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update time")


class McpProtocolHttp(Base):
    """MCP Protocol HTTP Configuration Model"""
    __tablename__ = "mcp_protocol_http"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    protocol_id = Column(BigInteger, nullable=False, comment="Protocol ID")
    http_url = Column(String(512), nullable=False, comment="HTTP URL")
    http_method = Column(String(16), nullable=False, default="POST", comment="HTTP method")
    http_headers = Column(Text, nullable=True, comment="HTTP headers JSON")
    timeout = Column(Integer, default=30000, comment="Timeout in milliseconds")
    retry_times = Column(SmallInteger, default=0, comment="Retry times")
    status = Column(SmallInteger, nullable=False, default=1, comment="Status")
    create_time = Column(DateTime, default=datetime.now, comment="Create time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update time")


class McpProtocolMapping(Base):
    """MCP Protocol Mapping Configuration Model"""
    __tablename__ = "mcp_protocol_mapping"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    protocol_id = Column(BigInteger, nullable=False, comment="Protocol ID")
    mapping_type = Column(String(32), nullable=False, comment="Mapping type: request/response")
    parent_path = Column(String(256), nullable=True, comment="Parent path")
    field_name = Column(String(128), nullable=False, comment="Field name")
    mcp_path = Column(String(256), nullable=False, comment="MCP full path")
    mcp_type = Column(String(32), nullable=False, comment="MCP data type")
    mcp_desc = Column(String(512), nullable=True, comment="MCP field description")
    is_required = Column(SmallInteger, nullable=False, default=0, comment="Is required: 0-no, 1-yes")
    sort_order = Column(Integer, default=0, comment="Sort order")
    create_time = Column(DateTime, default=datetime.now, comment="Create time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update time")
