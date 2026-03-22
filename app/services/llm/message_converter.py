# -*- coding: utf-8 -*-
"""
Anthropic Message Converter - Anthropic 消息格式转换器
将内部消息格式转换为 Anthropic API 所需格式
"""

from typing import List, Dict, Any, Tuple, Union


class AnthropicMessageConverter:
    """Anthropic API 消息转换器"""
    
    @staticmethod
    def convert(messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        将消息列表转换为 Anthropic API 格式
        
        Args:
            messages: 内部消息格式列表
            
        Returns:
            (system_prompt, anthropic_messages)
        """
        anthropic_messages = []
        system_prompt = ""
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content if isinstance(content, str) else str(content)
                
            elif role == "user":
                anthropic_messages.append(
                    AnthropicMessageConverter._convert_user_message(content)
                )
                
            elif role == "assistant":
                assistant_msg, user_msg = AnthropicMessageConverter._convert_assistant_message(content)
                if assistant_msg:
                    anthropic_messages.append(assistant_msg)
                if user_msg:
                    anthropic_messages.append(user_msg)
        
        return system_prompt, anthropic_messages
    
    @staticmethod
    def _convert_user_message(content: Union[str, List, Dict]) -> Dict[str, Any]:
        """转换用户消息"""
        if isinstance(content, str):
            return {
                "role": "user",
                "content": [{"type": "text", "text": content}]
            }
        else:
            return {"role": "user", "content": content}
    
    @staticmethod
    def _convert_assistant_message(content: Union[str, List, Dict]) -> Tuple[Dict, Dict]:
        """
        转换助手消息
        
        Returns:
            (assistant_message, user_message_with_tool_results)
            user_message 可能为 None
        """
        if isinstance(content, str):
            return {
                "role": "assistant",
                "content": [{"type": "text", "text": content}]
            }, None
        
        # 内容块列表
        assistant_content = []
        tool_result_content = []
        
        for block in content:
            if not isinstance(block, dict):
                continue
                
            block_type = block.get("type")
            
            if block_type == "thinking":
                assistant_content.append({
                    "type": "thinking",
                    "thinking": block.get("thinking", ""),
                })
                
            elif block_type == "text":
                assistant_content.append({
                    "type": "text",
                    "text": block.get("text", "")
                })
                
            elif block_type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                })
                
            elif block_type == "tool_result":
                # tool_result 必须放在 user 消息中
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": block.get("content", ""),
                })
        
        assistant_msg = None
        user_msg = None
        
        if assistant_content:
            assistant_msg = {"role": "assistant", "content": assistant_content}
        
        if tool_result_content:
            user_msg = {"role": "user", "content": tool_result_content}
        
        return assistant_msg, user_msg
    
    @staticmethod
    def build_request_kwargs(
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: List[Dict] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        tools_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        构建 API 请求参数
        
        Args:
            model: 模型名称
            messages: 消息列表
            system_prompt: 系统提示词
            tools: 工具列表
            max_tokens: 最大 token 数
            temperature: 温度参数
            tools_enabled: 是否启用工具
            
        Returns:
            API 请求参数字典
        """
        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        
        if system_prompt:
            request_kwargs["system"] = system_prompt
        
        if tools_enabled and tools:
            request_kwargs["tools"] = tools
        
        return request_kwargs