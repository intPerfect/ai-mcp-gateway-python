"""
Configuration management for MCP Gateway
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "123456"
    db_name: str = "ai_mcp_gateway_v2"
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8777
    
    # Session
    session_timeout_minutes: int = 30
    
    # LLM API
    llm_api_base_url: str = "https://api.minimaxi.com/v1"
    llm_model: str = "MiniMax-M2.5"
    llm_api_key: str = ""
    
    @property
    def database_url(self) -> str:
        """Get async database URL for SQLAlchemy"""
        return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
    
    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for SQLAlchemy"""
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
