# -*- coding: utf-8 -*-
"""
Message Manager - 消息管理器
统一管理消息格式转换和历史记录，确保消息历史完整性
"""

import json
import logging
import secrets
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import copy

logger = logging.getLogger(__name__)


class ContentBlockType(Enum):
    """内容块类型"""
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


@dataclass
class ContentBlock:
    """内容块基类"""
    type: str
    
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class TextBlock(ContentBlock):
    """文本块"""
    text: str = ""
    
    def __init__(self, text: str = ""):
        super().__init__(type=ContentBlockType.TEXT.value)
        self.text = text
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class ThinkingBlock(ContentBlock):
    """思考块"""
    thinking: str = ""
    
    def __init__(self, thinking: str = ""):
        super().__init__(type=ContentBlockType.THINKING.value)
        self.thinking = thinking
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "thinking": self.thinking}


@dataclass
class ToolUseBlock(ContentBlock):
    """工具使用块"""
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, id: str = "", name: str = "", input: Dict[str, Any] = None):
        super().__init__(type=ContentBlockType.TOOL_USE.value)
        self.id = id
        self.name = name
        self.input = input or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "id": self.id, "name": self.name, "input": self.input}


@dataclass
class ToolResultBlock(ContentBlock):
    """工具结果块"""
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False
    
    def __init__(self, tool_use_id: str = "", content: str = "", is_error: bool = False):
        super().__init__(type=ContentBlockType.TOOL_RESULT.value)
        self.tool_use_id = tool_use_id
        self.content = content
        self.is_error = is_error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type, 
            "tool_use_id": self.tool_use_id, 
            "content": self.content,
            "is_error": self.is_error
        }


class Message:
    """消息"""
    
    def __init__(self, role: str, content: Union[str, List[ContentBlock], List[Dict]] = ""):
        self.role = role  # system, user, assistant
        self.content = content
    
    def to_anthropic_format(self) -> Dict[str, Any]:
        """转换为 Anthropic API 格式"""
        if isinstance(self.content, str):
            if self.role == "system":
                return {"role": self.role, "content": self.content}
            else:
                return {"role": self.role, "content": [{"type": "text", "text": self.content}]}
        
        # 内容块列表
        blocks = []
        for block in self.content:
            if isinstance(block, ContentBlock):
                blocks.append(block.to_dict())
            elif isinstance(block, dict):
                blocks.append(block)
        
        return {"role": self.role, "content": blocks}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if isinstance(self.content, str):
            return {"role": self.role, "content": self.content}
        
        blocks = []
        for block in self.content:
            if isinstance(block, ContentBlock):
                blocks.append(block.to_dict())
            elif isinstance(block, dict):
                blocks.append(block)
        
        return {"role": self.role, "content": blocks}


class MessageHistory:
    """消息历史管理器"""
    
    def __init__(self, system_prompt: str = ""):
        self.messages: List[Message] = []
        self._system_prompt = system_prompt
        
        # 初始化系统消息
        if system_prompt:
            self.messages.append(Message("system", system_prompt))
    
    @property
    def system_prompt(self) -> str:
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, prompt: str):
        self._system_prompt = prompt
        # 更新或添加系统消息
        if self.messages and self.messages[0].role == "system":
            self.messages[0] = Message("system", prompt)
        else:
            self.messages.insert(0, Message("system", prompt))
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append(Message("user", content))
        logger.debug(f"添加用户消息: {content[:50]}...")
    
    def add_assistant_message(self, content: Union[str, List[ContentBlock], List[Dict]]):
        """添加助手消息"""
        self.messages.append(Message("assistant", content))
        if isinstance(content, str):
            logger.debug(f"添加助手消息(text): {content[:50]}...")
        else:
            logger.debug(f"添加助手消息(blocks): {len(content)} blocks")
    
    def add_tool_result(self, tool_use_id: str, result: Any, is_error: bool = False):
        """
        添加工具结果（作为 user 消息）
        注意：Anthropic API 要求 tool_result 放在 user 角色的消息中
        """
        result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
        tool_result_block = ToolResultBlock(
            tool_use_id=tool_use_id,
            content=result_str,
            is_error=is_error
        )
        
        # 检查最后一条消息是否是 user 消息且只包含 tool_result
        # 如果是，可以追加到该消息中；否则创建新消息
        if self.messages and self.messages[-1].role == "user":
            last_content = self.messages[-1].content
            if isinstance(last_content, list):
                # 检查是否全是 tool_result
                all_tool_results = all(
                    (isinstance(b, ToolResultBlock) or 
                     (isinstance(b, dict) and b.get("type") == "tool_result"))
                    for b in last_content
                )
                if all_tool_results:
                    last_content.append(tool_result_block)
                    logger.debug(f"追加工具结果到现有消息: {tool_use_id}")
                    return
        
        # 创建新的 user 消息
        self.messages.append(Message("user", [tool_result_block]))
        logger.debug(f"添加新工具结果消息: {tool_use_id}")
    
    def add_tool_results_batch(self, results: List[Dict[str, Any]]):
        """批量添加工具结果"""
        if not results:
            return
        
        blocks = []
        for r in results:
            tool_use_id = r.get("tool_use_id", "")
            result = r.get("result", {})
            is_error = r.get("is_error", False)
            
            result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
            blocks.append(ToolResultBlock(
                tool_use_id=tool_use_id,
                content=result_str,
                is_error=is_error
            ))
        
        self.messages.append(Message("user", blocks))
        logger.debug(f"批量添加 {len(blocks)} 个工具结果")
    
    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """获取用于 API 调用的消息列表"""
        result = []
        for msg in self.messages:
            result.append(msg.to_anthropic_format())
        return result
    
    def get_messages_copy(self) -> List[Dict[str, Any]]:
        """获取消息的深拷贝"""
        return [msg.to_dict() for msg in self.messages]
    
    def clear(self, keep_system: bool = True):
        """清空消息历史"""
        if keep_system and self.messages and self.messages[0].role == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
    
    def get_last_assistant_message(self) -> Optional[Message]:
        """获取最后一条助手消息"""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg
        return None
    
    def get_last_user_message(self) -> Optional[Message]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None
    
    def __len__(self):
        return len(self.messages)
    
    def __repr__(self):
        return f"MessageHistory(messages={len(self.messages)})"


class MessageBuilder:
    """消息构建器 - 辅助构建复杂消息"""
    
    @staticmethod
    def build_assistant_response(
        text: str = "",
        thinking: str = "",
        tool_calls: List[Dict] = None
    ) -> List[ContentBlock]:
        """构建助手响应内容块"""
        blocks = []
        
        # 先添加思考块（如果有）
        if thinking:
            blocks.append(ThinkingBlock(thinking=thinking))
        
        # 再添加文本块（如果有）
        if text:
            blocks.append(TextBlock(text=text))
        
        # 最后添加工具调用块（如果有）
        if tool_calls:
            for tc in tool_calls:
                blocks.append(ToolUseBlock(
                    id=tc.get("id", f"tool_{secrets.token_hex(8)}"),
                    name=tc.get("name", ""),
                    input=tc.get("input", {})
                ))
        
        return blocks
    
    @staticmethod
    def parse_llm_content_blocks(content_blocks: List[Dict]) -> Dict[str, Any]:
        """
        解析 LLM 返回的内容块
        返回: {text: str, thinking: str, tool_calls: List[Dict]}
        """
        text_parts = []
        thinking_parts = []
        tool_calls = []
        
        for block in content_blocks:
            block_type = block.get("type", "")
            
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "thinking":
                thinking_parts.append(block.get("thinking", ""))
            elif block_type == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {})
                })
        
        return {
            "text": "".join(text_parts),
            "thinking": "".join(thinking_parts),
            "tool_calls": tool_calls
        }
    
    @staticmethod
    def merge_content_blocks(existing: List[ContentBlock], new_blocks: List[ContentBlock]) -> List[ContentBlock]:
        """合并内容块（智能合并相邻的同类型块）"""
        if not existing:
            return new_blocks
        if not new_blocks:
            return existing
        
        result = copy.deepcopy(existing)
        
        for new_block in new_blocks:
            # 检查是否可以合并到最后一个块
            if result and isinstance(result[-1], type(new_block)):
                last = result[-1]
                if isinstance(new_block, TextBlock) and isinstance(last, TextBlock):
                    last.text += new_block.text
                    continue
                elif isinstance(new_block, ThinkingBlock) and isinstance(last, ThinkingBlock):
                    last.thinking += new_block.thinking
                    continue
            
            # 不能合并，直接添加
            result.append(copy.deepcopy(new_block))
        
        return result