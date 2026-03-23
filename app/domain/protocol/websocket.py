# -*- coding: utf-8 -*-
"""
WebSocket Protocol - 统一的WebSocket事件协议
定义后端网关与前端之间的标准化通信协议
兼容各种LLM输出格式，对前端提供统一接口
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


# ============ 事件类型定义 ============

class WSEventType(Enum):
    """WebSocket事件类型 - 统一标准"""
    
    # 连接相关
    WELCOME = "welcome"           # 连接成功欢迎消息
    PONG = "pong"                 # 心跳响应
    
    # 对话流程
    STREAM_START = "stream_start"     # 流式输出开始
    STREAM_END = "stream_end"         # 流式输出结束（内部用，不直接发送）
    
    # 内容输出
    TEXT_DELTA = "text_delta"         # 文本增量
    TEXT_STOP = "text_stop"           # 文本块结束
    THINKING_DELTA = "thinking_delta" # 思考过程增量
    THINKING_STOP = "thinking_stop"   # 思考块结束
    
    # 工具调用
    TOOL_USE_START = "tool_use_start" # 工具调用开始（LLM声明要调用）
    TOOL_USE_STOP = "tool_use_stop"   # 工具调用声明结束
    TOOL_CALL = "tool_call"           # 工具开始执行
    TOOL_RESULT = "tool_result"       # 工具执行结果
    
    # 状态与控制
    STATUS = "status"                 # 状态更新（思考中、执行工具等）
    RESPONSE = "response"             # 最终响应
    ERROR = "error"                   # 错误
    
    # 会话控制
    CLEARED = "cleared"               # 对话已清空


# ============ 事件构建器 ============

@dataclass
class WSEvent:
    """WebSocket事件基类"""
    type: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type}
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class WelcomeEvent(WSEvent):
    """欢迎事件"""
    session_id: str = ""
    tools: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        self.type = WSEventType.WELCOME.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "tools": self.tools
        }


@dataclass
class StreamStartEvent(WSEvent):
    """流开始事件"""
    
    def __post_init__(self):
        self.type = WSEventType.STREAM_START.value


@dataclass
class TextDeltaEvent(WSEvent):
    """文本增量事件"""
    text: str = ""
    
    def __post_init__(self):
        self.type = WSEventType.TEXT_DELTA.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text
        }


@dataclass
class TextStopEvent(WSEvent):
    """文本结束事件"""
    text: str = ""  # 完整文本
    
    def __post_init__(self):
        self.type = WSEventType.TEXT_STOP.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text
        }


@dataclass
class ThinkingDeltaEvent(WSEvent):
    """思考增量事件"""
    thinking: str = ""                    # 当前增量
    accumulated: str = ""                 # 本轮累积内容
    round: int = 1                        # 当前轮次，前端据此创建独立块
    
    def __post_init__(self):
        self.type = WSEventType.THINKING_DELTA.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "thinking": self.thinking,
            "accumulated": self.accumulated,
            "round": self.round
        }


@dataclass
class ThinkingStopEvent(WSEvent):
    """思考结束事件"""
    thinking: str = ""  # 完整思考内容
    
    def __post_init__(self):
        self.type = WSEventType.THINKING_STOP.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "thinking": self.thinking
        }


@dataclass
class ToolUseStartEvent(WSEvent):
    """工具调用声明开始事件"""
    id: str = ""
    name: str = ""
    
    def __post_init__(self):
        self.type = WSEventType.TOOL_USE_START.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "id": self.id,
            "name": self.name
        }


@dataclass
class ToolUseStopEvent(WSEvent):
    """工具调用声明结束事件"""
    
    def __post_init__(self):
        self.type = WSEventType.TOOL_USE_STOP.value


@dataclass
class ToolCallEvent(WSEvent):
    """工具执行事件"""
    tool_id: str = ""
    tool: str = ""           # 工具名称
    arguments: Dict = field(default_factory=dict)
    status: str = "executing"  # executing, completed, failed
    
    def __post_init__(self):
        self.type = WSEventType.TOOL_CALL.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "tool_id": self.tool_id,
            "tool": self.tool,
            "arguments": self.arguments,
            "status": self.status
        }


@dataclass
class ToolResultEvent(WSEvent):
    """工具结果事件"""
    tool_id: str = ""
    tool: str = ""
    result: Any = None
    success: bool = True
    
    def __post_init__(self):
        self.type = WSEventType.TOOL_RESULT.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "tool_id": self.tool_id,
            "tool": self.tool,
            "result": self.result,
            "success": self.success
        }


@dataclass
class StatusEvent(WSEvent):
    """状态事件"""
    status: str = ""         # thinking, executing_tools, tools_completed, cleared
    message: str = ""
    data: Dict = field(default_factory=dict)  # 额外数据
    
    def __post_init__(self):
        self.type = WSEventType.STATUS.value
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "status": self.status,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class ResponseEvent(WSEvent):
    """最终响应事件"""
    content: str = ""
    thinking: str = ""
    tool_calls: List[str] = field(default_factory=list)
    rounds: int = 0
    limit_reached: bool = False
    
    def __post_init__(self):
        self.type = WSEventType.RESPONSE.value
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "rounds": self.rounds
        }
        if self.thinking:
            result["thinking"] = self.thinking
        if self.limit_reached:
            result["limit_reached"] = self.limit_reached
        return result


@dataclass
class ErrorEvent(WSEvent):
    """错误事件"""
    message: str = ""
    code: Optional[str] = None
    
    def __post_init__(self):
        self.type = WSEventType.ERROR.value
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "message": self.message
        }
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class ClearedEvent(WSEvent):
    """清空事件"""
    message: str = "对话已清空"
    
    def __post_init__(self):
        self.type = WSEventType.STATUS.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "status": "cleared",
            "message": self.message
        }


@dataclass
class PongEvent(WSEvent):
    """心跳响应事件"""
    
    def __post_init__(self):
        self.type = WSEventType.PONG.value


# ============ 事件工厂 ============

class WSEventFactory:
    """WebSocket事件工厂 - 统一创建事件"""
    
    @staticmethod
    def welcome(session_id: str, tools: List[Dict]) -> Dict[str, Any]:
        """创建欢迎事件"""
        return WelcomeEvent(session_id=session_id, tools=tools).to_dict()
    
    @staticmethod
    def stream_start() -> Dict[str, Any]:
        """创建流开始事件"""
        return StreamStartEvent().to_dict()
    
    @staticmethod
    def text_delta(text: str) -> Dict[str, Any]:
        """创建文本增量事件"""
        return TextDeltaEvent(text=text).to_dict()
    
    @staticmethod
    def text_stop(text: str) -> Dict[str, Any]:
        """创建文本结束事件"""
        return TextStopEvent(text=text).to_dict()
    
    @staticmethod
    def thinking_delta(thinking: str, accumulated: str = "", round: int = 1) -> Dict[str, Any]:
        """创建思考增量事件"""
        return ThinkingDeltaEvent(thinking=thinking, accumulated=accumulated, round=round).to_dict()
    
    @staticmethod
    def thinking_stop(thinking: str) -> Dict[str, Any]:
        """创建思考结束事件"""
        return ThinkingStopEvent(thinking=thinking).to_dict()
    
    @staticmethod
    def tool_use_start(tool_id: str, tool_name: str) -> Dict[str, Any]:
        """创建工具调用声明开始事件"""
        return ToolUseStartEvent(id=tool_id, name=tool_name).to_dict()
    
    @staticmethod
    def tool_use_stop() -> Dict[str, Any]:
        """创建工具调用声明结束事件"""
        return ToolUseStopEvent().to_dict()
    
    @staticmethod
    def tool_call(tool_id: str, tool_name: str, arguments: Dict, status: str = "executing") -> Dict[str, Any]:
        """创建工具执行事件"""
        return ToolCallEvent(
            tool_id=tool_id, 
            tool=tool_name, 
            arguments=arguments, 
            status=status
        ).to_dict()
    
    @staticmethod
    def tool_result(tool_id: str, tool_name: str, result: Any, success: bool = True) -> Dict[str, Any]:
        """创建工具结果事件"""
        return ToolResultEvent(
            tool_id=tool_id,
            tool=tool_name,
            result=result,
            success=success
        ).to_dict()
    
    @staticmethod
    def status(status: str, message: str = "", **extra) -> Dict[str, Any]:
        """创建状态事件"""
        return StatusEvent(status=status, message=message, data=extra).to_dict()
    
    @staticmethod
    def response(content: str, thinking: str = "", tool_calls: List[str] = None, rounds: int = 0) -> Dict[str, Any]:
        """创建最终响应事件"""
        return ResponseEvent(
            content=content,
            thinking=thinking,
            tool_calls=tool_calls or [],
            rounds=rounds
        ).to_dict()
    
    @staticmethod
    def error(message: str, code: str = None) -> Dict[str, Any]:
        """创建错误事件"""
        return ErrorEvent(message=message, code=code).to_dict()
    
    @staticmethod
    def cleared() -> Dict[str, Any]:
        """创建清空事件"""
        return ClearedEvent().to_dict()
    
    @staticmethod
    def pong() -> Dict[str, Any]:
        """创建心跳响应事件"""
        return PongEvent().to_dict()


# ============ 协议文档 ============

WEBSOCKET_PROTOCOL_DOC = """
# WebSocket 协议文档

## 事件格式
所有事件均为 JSON 格式，包含 `type` 字段标识事件类型。

## 事件列表

### 1. 连接事件

#### welcome - 欢迎消息
```json
{
  "type": "welcome",
  "session_id": "session_xxx",
  "tools": [{"name": "tool_name", "description": "...", "input_schema": {...}}]
}
```

#### pong - 心跳响应
```json
{"type": "pong"}
```

### 2. 流式输出事件

#### stream_start - 流开始
```json
{"type": "stream_start"}
```

#### text_delta - 文本增量
```json
{
  "type": "text_delta",
  "text": "新增文本片段"
}
```

#### text_stop - 文本结束
```json
{
  "type": "text_stop",
  "text": "完整文本内容"
}
```

#### thinking_delta - 思考增量
```json
{
  "type": "thinking_delta",
  "thinking": "当前思考片段",
  "accumulated": "累积的完整思考内容"
}
```

### 3. 工具调用事件

#### tool_use_start - 工具调用声明开始
```json
{
  "type": "tool_use_start",
  "id": "tool_xxx",
  "name": "get_products"
}
```

#### tool_use_stop - 工具调用声明结束
```json
{"type": "tool_use_stop"}
```

#### tool_call - 工具执行
```json
{
  "type": "tool_call",
  "tool_id": "tool_xxx",
  "tool": "get_products",
  "arguments": {"category": "electronics"},
  "status": "executing"
}
```

#### tool_result - 工具结果
```json
{
  "type": "tool_result",
  "tool_id": "tool_xxx",
  "tool": "get_products",
  "result": {"products": [...]},
  "success": true
}
```

### 4. 状态与控制事件

#### status - 状态更新
```json
{
  "type": "status",
  "status": "thinking",  // thinking, executing_tools, tools_completed
  "message": "正在思考..."
}
```

#### response - 最终响应
```json
{
  "type": "response",
  "content": "最终回复文本",
  "thinking": "完整思考过程",
  "tool_calls": ["get_products", "check_inventory"],
  "rounds": 2
}
```

#### error - 错误
```json
{
  "type": "error",
  "message": "错误描述",
  "code": "ERROR_CODE"  // 可选
}
```

## 客户端请求格式

### chat - 发送消息
```json
{
  "type": "chat",
  "content": "用户消息内容"
}
```

### clear - 清空对话
```json
{"type": "clear"}
```

### ping - 心跳
```json
{"type": "ping"}
```
"""
