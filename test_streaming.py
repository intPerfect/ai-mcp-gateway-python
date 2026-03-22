# -*- coding: utf-8 -*-
"""
流式输出测试脚本 - 验证 WebSocket 消息格式
"""
import asyncio
import json
import websockets
import sys

# 测试配置
API_BASE_URL = "http://localhost:8777"
WS_URL = "ws://localhost:8777/ws/chat"
GATEWAY_KEY = "gw-test-api-key-001"
LLM_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLnmb7ono3kupHliJsiLCJVc2VyTmFtZSI6IueZvuiejeS6keWImyIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTk4NjY2Nzg0MTg5NzE0Njk5IiwiUGhvbmUiOiIxOTUxMTk4MTY4OSIsIkdyb3VwSUQiOiIxOTk4NjY2Nzg0MTgxMzI2MDkxIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjUtMTItMTAgMjE6MzI6MTYiLCJUb2tlblR5cGUiOjQsImlzcyI6Im1pbmltYXgifQ.u5vB41nODwjoj-a728IeKgtdnoL7AC0rJbw3Uv8iXA6CVqXQ3SY5RCTo87yAzAeva8prR4YcBQ-nIG5mtXYd_jemI-mjA909hYN3yvWsjuD4m_3U2SqoDY5E6vV6gyGPzQlnB0OkzOKJCwQbb6FUfcymWTSiAtw2k8DgfCeQLJLUMKmxOjHYOontut_gujCxY57wU-8h0p4PWkS74hLnritLO3oIBq6ZNmf1d3uC4pw-jVCflSlymm16luObc-DeohNc83fAOtMPSJ76mi_bdAcoIgCOyAP3VUan53QyLHwzcq-i8YI-TuxkAvH3slauNsHAfUWNhlqJouRXdFwsHg"

# 消息计数器
message_stats = {
    "total": 0,
    "types": {}
}


def log_message(msg_type: str, data: dict):
    """记录消息"""
    message_stats["total"] += 1
    message_stats["types"][msg_type] = message_stats["types"].get(msg_type, 0) + 1
    
    # 打印消息摘要
    if msg_type == "welcome":
        tools = data.get("tools", [])
        print(f"[WELCOME] 会话ID: {data.get('session_id', 'N/A')}, 工具数量: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description', 'N/A')[:50]}...")
    
    elif msg_type == "stream_start":
        print("[STREAM_START] 流式输出开始")
    
    elif msg_type == "text_delta":
        text = data.get("text", "")
        print(f"[TEXT_DELTA] {repr(text)}")
    
    elif msg_type == "thinking_delta":
        thinking = data.get("thinking", "")
        print(f"[THINKING_DELTA] {repr(thinking[:100])}...")
    
    elif msg_type == "tool_use_start":
        print(f"[TOOL_USE_START] 工具: {data.get('name')}, ID: {data.get('id')}")
    
    elif msg_type == "tool_call":
        print(f"[TOOL_CALL] 工具: {data.get('tool')}, 状态: {data.get('status')}")
        print(f"  参数: {json.dumps(data.get('arguments', {}), ensure_ascii=False)[:200]}")
    
    elif msg_type == "tool_result":
        print(f"[TOOL_RESULT] 工具: {data.get('tool')}")
        result = data.get("result", {})
        if isinstance(result, dict):
            print(f"  结果: code={result.get('code')}, message={result.get('message')}")
        else:
            print(f"  结果: {str(result)[:200]}")
    
    elif msg_type == "response":
        print(f"[RESPONSE] 最终响应")
        print(f"  内容长度: {len(data.get('content', ''))}")
        print(f"  工具调用: {data.get('tool_calls', [])}")
    
    elif msg_type == "error":
        print(f"[ERROR] {data.get('message', 'Unknown error')}")
    
    elif msg_type == "status":
        print(f"[STATUS] {data.get('status')}: {data.get('message', '')}")
    
    else:
        print(f"[{msg_type.upper()}] {json.dumps(data, ensure_ascii=False)[:200]}")


async def test_streaming():
    """测试流式输出"""
    print("=" * 60)
    print("流式输出测试 - 问题: '有哪些商品？'")
    print("=" * 60)
    
    # 第一步：创建会话
    print("\n[1] 创建会话...")
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}/api/chat/session",
            json={"gateway_key": GATEWAY_KEY, "llm_key": LLM_KEY}
        ) as resp:
            if resp.status != 200:
                print(f"创建会话失败: {resp.status}")
                return
            
            result = await resp.json()
            session_id = result.get("session_id")
            ws_path = result.get("websocket_url")
            print(f"会话创建成功: {session_id}")
            print(f"WebSocket路径: {ws_path}")
    
    # 第二步：连接 WebSocket
    print("\n[2] 连接 WebSocket...")
    ws_url = f"ws://localhost:8777{ws_path}"
    
    async with websockets.connect(ws_url) as ws:
        print(f"已连接到: {ws_url}")
        
        # 接收欢迎消息
        welcome_msg = await ws.recv()
        welcome_data = json.loads(welcome_msg)
        log_message(welcome_data.get("type"), welcome_data)
        
        # 第三步：发送问题
        print("\n[3] 发送问题: '有哪些商品？'")
        await ws.send(json.dumps({"type": "chat", "content": "有哪些商品？"}))
        
        # 第四步：接收流式响应
        print("\n[4] 接收流式响应...")
        print("-" * 60)
        
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60)
                data = json.loads(msg)
                msg_type = data.get("type")
                
                log_message(msg_type, data)
                
                # 收到最终响应或错误时结束
                if msg_type in ["response", "error"]:
                    break
                    
        except asyncio.TimeoutError:
            print("\n[TIMEOUT] 等待响应超时")
        
        print("-" * 60)
    
    # 打印统计
    print("\n[5] 消息统计:")
    print(f"总消息数: {message_stats['total']}")
    print("消息类型分布:")
    for msg_type, count in sorted(message_stats["types"].items()):
        print(f"  {msg_type}: {count}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_streaming())
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
