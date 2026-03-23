# -*- coding: utf-8 -*-
"""
Conversation Logger - 对话日志服务
结构化记录 LLM 对话的输入输出，支持文件和数据库双写
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class LogEventType(Enum):
    """日志事件类型"""
    USER_INPUT = "user_input"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_THINKING = "llm_thinking"
    LLM_TEXT = "llm_text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class ConversationEvent:
    """对话事件"""
    timestamp: str
    session_id: str
    event_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class ConversationLogger:
    """对话日志记录器"""
    
    def __init__(self, log_dir: str = "logs/conversations"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._session_logs: Dict[str, List[ConversationEvent]] = {}
        self._write_lock = asyncio.Lock()
    
    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _get_session_file(self, session_id: str) -> Path:
        # 按日期分目录
        date_dir = self.log_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir / f"{session_id}.jsonl"
    
    def _create_event(
        self, 
        session_id: str, 
        event_type: LogEventType, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationEvent:
        return ConversationEvent(
            timestamp=self._get_timestamp(),
            session_id=session_id,
            event_type=event_type.value,
            data=data,
            metadata=metadata or {}
        )
    
    async def log_event(
        self, 
        session_id: str, 
        event_type: LogEventType, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录事件（内存 + 文件）"""
        event = self._create_event(session_id, event_type, data, metadata)
        
        # 存入内存
        if session_id not in self._session_logs:
            self._session_logs[session_id] = []
        self._session_logs[session_id].append(event)
        
        # 写入文件（异步）
        await self._write_to_file(session_id, event)
        
        # 同时输出到控制台日志
        self._log_to_console(event)
    
    async def _write_to_file(self, session_id: str, event: ConversationEvent):
        """写入日志文件"""
        try:
            async with self._write_lock:
                file_path = self._get_session_file(session_id)
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error(f"写入对话日志文件失败: {e}")
    
    def _log_to_console(self, event: ConversationEvent):
        """输出到控制台"""
        event_type = event.event_type
        data = event.data
        
        if event_type == LogEventType.USER_INPUT.value:
            logger.info(f"[{event.session_id}] 用户输入: {data.get('content', '')[:100]}")
        
        elif event_type == LogEventType.LLM_REQUEST.value:
            msg_count = data.get('message_count', 0)
            tools_enabled = data.get('tools_enabled', False)
            logger.info(f"[{event.session_id}] LLM请求: messages={msg_count}, tools={tools_enabled}")
        
        elif event_type == LogEventType.LLM_RESPONSE.value:
            has_tool_calls = len(data.get('tool_calls', [])) > 0
            text_len = len(data.get('text', ''))
            logger.info(f"[{event.session_id}] LLM响应: text_len={text_len}, tool_calls={has_tool_calls}")
        
        elif event_type == LogEventType.TOOL_CALL.value:
            tool_name = data.get('name', '')
            logger.info(f"[{event.session_id}] 工具调用: {tool_name}")
        
        elif event_type == LogEventType.TOOL_RESULT.value:
            tool_name = data.get('name', '')
            success = data.get('success', False)
            logger.info(f"[{event.session_id}] 工具结果: {tool_name}, success={success}")
        
        elif event_type == LogEventType.ERROR.value:
            logger.error(f"[{event.session_id}] 错误: {data.get('message', '')}")
        
        elif event_type == LogEventType.SESSION_START.value:
            logger.info(f"[{event.session_id}] 会话开始")
        
        elif event_type == LogEventType.SESSION_END.value:
            rounds = data.get('tool_rounds', 0)
            tools = data.get('tools_called', [])
            logger.info(f"[{event.session_id}] 会话结束: rounds={rounds}, tools={tools}")
    
    # ============ 便捷方法 ============
    
    async def log_session_start(self, session_id: str, gateway_key: str = "", llm_key_prefix: str = ""):
        """记录会话开始"""
        await self.log_event(
            session_id,
            LogEventType.SESSION_START,
            {
                "gateway_key_prefix": gateway_key[:10] + "..." if gateway_key else "",
                "llm_key_prefix": llm_key_prefix[:10] + "..." if llm_key_prefix else ""
            }
        )
    
    async def log_user_input(self, session_id: str, content: str):
        """记录用户输入"""
        await self.log_event(
            session_id,
            LogEventType.USER_INPUT,
            {"content": content}
        )
    
    async def log_llm_request(
        self, 
        session_id: str, 
        messages: List[Dict], 
        tools_enabled: bool,
        round_num: int = 0
    ):
        """记录LLM请求"""
        # 简化消息历史，避免日志过大
        simplified_messages = []
        for i, msg in enumerate(messages[-10:]):  # 只记录最近10条
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str):
                content_preview = content[:200] + "..." if len(content) > 200 else content
            elif isinstance(content, list):
                # 内容块列表
                content_preview = f"[{len(content)} blocks: " + ", ".join(
                    b.get("type", "unknown") if isinstance(b, dict) else "unknown" 
                    for b in content[:5]
                ) + "]"
            else:
                content_preview = str(type(content))
            
            simplified_messages.append({
                "index": i,
                "role": role,
                "content_preview": content_preview
            })
        
        await self.log_event(
            session_id,
            LogEventType.LLM_REQUEST,
            {
                "message_count": len(messages),
                "tools_enabled": tools_enabled,
                "round": round_num,
                "messages_summary": simplified_messages
            }
        )
    
    async def log_llm_thinking(self, session_id: str, thinking: str, round_num: int = 0):
        """记录LLM思考过程"""
        await self.log_event(
            session_id,
            LogEventType.LLM_THINKING,
            {
                "thinking": thinking,
                "round": round_num
            }
        )
    
    async def log_llm_text(self, session_id: str, text: str, round_num: int = 0):
        """记录LLM文本输出"""
        await self.log_event(
            session_id,
            LogEventType.LLM_TEXT,
            {
                "text": text,
                "round": round_num
            }
        )
    
    async def log_llm_response(
        self, 
        session_id: str, 
        text: str, 
        tool_calls: List[Dict],
        round_num: int = 0
    ):
        """记录LLM完整响应"""
        await self.log_event(
            session_id,
            LogEventType.LLM_RESPONSE,
            {
                "text": text,
                "tool_calls": [
                    {"name": tc.get("name"), "input": tc.get("input")}
                    for tc in tool_calls
                ],
                "round": round_num
            }
        )
    
    async def log_tool_call(
        self, 
        session_id: str, 
        tool_id: str, 
        tool_name: str, 
        arguments: Dict,
        round_num: int = 0
    ):
        """记录工具调用"""
        await self.log_event(
            session_id,
            LogEventType.TOOL_CALL,
            {
                "tool_id": tool_id,
                "name": tool_name,
                "arguments": arguments,
                "round": round_num
            }
        )
    
    async def log_tool_result(
        self, 
        session_id: str, 
        tool_id: str,
        tool_name: str, 
        result: Any,
        success: bool = True,
        round_num: int = 0
    ):
        """记录工具结果"""
        # 限制结果大小
        result_str = json.dumps(result, ensure_ascii=False, default=str)
        if len(result_str) > 1000:
            result_preview = result_str[:1000] + "...(truncated)"
        else:
            result_preview = result
        
        await self.log_event(
            session_id,
            LogEventType.TOOL_RESULT,
            {
                "tool_id": tool_id,
                "name": tool_name,
                "result_preview": result_preview,
                "success": success,
                "round": round_num
            }
        )
    
    async def log_error(self, session_id: str, error: str, context: Optional[Dict] = None):
        """记录错误"""
        await self.log_event(
            session_id,
            LogEventType.ERROR,
            {
                "message": error,
                "context": context or {}
            }
        )
    
    async def log_session_end(
        self, 
        session_id: str, 
        tool_rounds: int, 
        tools_called: List[str]
    ):
        """记录会话结束"""
        await self.log_event(
            session_id,
            LogEventType.SESSION_END,
            {
                "tool_rounds": tool_rounds,
                "tools_called": tools_called
            }
        )
        
        # 清理内存中的日志（保留文件）
        if session_id in self._session_logs:
            del self._session_logs[session_id]
    
    def get_session_log(self, session_id: str) -> List[ConversationEvent]:
        """获取会话日志（内存中）"""
        return self._session_logs.get(session_id, [])
    
    async def get_session_log_from_file(self, session_id: str) -> List[Dict]:
        """从文件读取会话日志"""
        file_path = self._get_session_file(session_id)
        if not file_path.exists():
            return []
        
        events = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            logger.error(f"读取会话日志文件失败: {e}")
        
        return events


# 全局单例
conversation_logger = ConversationLogger()
