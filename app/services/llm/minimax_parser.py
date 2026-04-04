# -*- coding: utf-8 -*-
"""
MiniMax XML Tool Call Parser
解析 MiniMax 返回的 XML 格式工具调用
"""

import re
import secrets
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


def parse_minimax_tool_calls(text: str) -> Tuple[str, List[Dict]]:
    """
    解析 MiniMax 返回的 XML 格式工具调用
    格式: <minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>

    Returns:
        (clean_text, tool_calls)
    """
    tool_calls = []
    clean_text = text

    pattern = r"<minimax:tool_call>(.*?)</minimax:tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            name_match = re.search(r'<invoke\s+name=["\']([^"\']+)["\']', match)
            if not name_match:
                continue
            tool_name = name_match.group(1)

            params = {}
            for param in re.finditer(
                r'<parameter\s+name=["\']([^"\']+)["\']>(.*?)</parameter>',
                match,
                re.DOTALL,
            ):
                params[param.group(1)] = param.group(2).strip()

            tool_calls.append(
                {
                    "id": f"tool_{secrets.token_hex(8)}",
                    "name": tool_name,
                    "input": params,
                }
            )
        except Exception as e:
            logger.warning(f"解析 minimax tool_call 失败: {e}")

    clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
    return clean_text, tool_calls
