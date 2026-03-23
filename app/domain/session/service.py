"""
Session management service
"""
import uuid
import asyncio
import logging
import secrets
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from app.config import get_settings
from app.domain.session.models import SessionConfig

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PendingSession:
    """待连接的WebSocket会话信息"""
    gateway_key: str
    llm_key: str
    microservice_ids: Optional[List[int]] = None


class WebSocketSessionManager:
    """WebSocket会话管理器 - 管理待连接的会话"""
    
    def __init__(self):
        self.pending_sessions: Dict[str, PendingSession] = {}
    
    def create_pending_session(
        self, 
        gateway_key: str, 
        llm_key: str,
        microservice_ids: Optional[List[int]] = None
    ) -> str:
        """创建待连接的会话"""
        session_id = f"session_{secrets.token_hex(16)}"
        self.pending_sessions[session_id] = PendingSession(
            gateway_key, llm_key, microservice_ids
        )
        logger.info(f"创建待连接会话: {session_id}, 微服务筛选: {microservice_ids}")
        return session_id
    
    def get_pending_session(self, session_id: str) -> Optional[PendingSession]:
        """获取并移除待连接会话"""
        return self.pending_sessions.pop(session_id, None)


# 全局WebSocket会话管理器
ws_session_manager = WebSocketSessionManager()


class SessionManagementService:
    """Service for managing MCP sessions"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionConfig] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start session management service"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        logger.info(f"Session management service started, timeout: {settings.session_timeout_minutes} minutes")
    
    async def stop(self):
        """Stop session management service"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        for session_id in list(self._sessions.keys()):
            await self.remove_session(session_id)
        
        logger.info("Session management service stopped")
    
    async def create_session(self, gateway_id: str, api_key: str) -> SessionConfig:
        """
        Create a new session
        
        Args:
            gateway_id: Gateway identifier
            api_key: API key for authentication
            
        Returns:
            Created session configuration
        """
        session_id = str(uuid.uuid4())
        
        session = SessionConfig(
            session_id=session_id,
            gateway_id=gateway_id,
            api_key=api_key
        )
        
        self._sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for gateway {gateway_id}, active sessions: {len(self._sessions)}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionConfig]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session configuration or None
        """
        session = self._sessions.get(session_id)
        
        if session and session.is_active:
            session.update_last_accessed()
            return session
        
        return None
    
    async def remove_session(self, session_id: str):
        """
        Remove session
        
        Args:
            session_id: Session identifier
        """
        session = self._sessions.pop(session_id, None)
        
        if session:
            session.mark_inactive()
            # Signal queue to close
            await session.message_queue.put(None)
            logger.info(f"Removed session {session_id}, remaining sessions: {len(self._sessions)}")
    
    async def _cleanup_expired_sessions(self):
        """Background task to clean up expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                expired = []
                for session_id, session in self._sessions.items():
                    if not session.is_active or session.is_expired(settings.session_timeout_minutes):
                        expired.append(session_id)
                
                for session_id in expired:
                    await self.remove_session(session_id)
                
                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired sessions, remaining: {len(self._sessions)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")


# Global session manager instance
session_manager = SessionManagementService()
