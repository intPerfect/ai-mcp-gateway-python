# -*- coding: utf-8 -*-
"""
Constants - 应用常量定义
集中管理所有魔法字符串和硬编码值
"""


class ToolStatus:
    """工具状态常量"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ChatState:
    """对话状态常量"""
    IDLE = "idle"
    PROCESSING = "processing"
    TOOL_CALLING = "tool_calling"
    COMPLETED = "completed"
    ERROR = "error"


class WSEventType:
    """WebSocket 事件类型常量"""
    # 连接相关
    WELCOME = "welcome"
    PONG = "pong"
    
    # 对话流程
    STREAM_START = "stream_start"
    STREAM_END = "stream_end"
    
    # 内容输出
    TEXT_DELTA = "text_delta"
    TEXT_STOP = "text_stop"
    THINKING_DELTA = "thinking_delta"
    THINKING_STOP = "thinking_stop"
    
    # 工具调用
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_STOP = "tool_use_stop"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    
    # 状态与控制
    STATUS = "status"
    RESPONSE = "response"
    ERROR = "error"
    
    # 会话控制
    CLEARED = "cleared"


class MessageType:
    """消息类型常量"""
    CHAT = "chat"
    CLEAR = "clear"
    PING = "ping"


class ErrorCode:
    """错误码常量"""
    MISSING_SESSION_ID = 4001
    INVALID_SESSION_ID = 4002
    SESSION_NOT_FOUND = 4003
    TOOL_NOT_FOUND = 5001
    TOOL_EXECUTION_ERROR = 5002
    LLM_API_ERROR = 5003


class DefaultValues:
    """默认值常量"""
    DEFAULT_GATEWAY_ID = "gateway_001"
    DEFAULT_SERVER_HOST = "0.0.0.0"
    DEFAULT_SERVER_PORT = 8777
    DEFAULT_SESSION_TIMEOUT_MINUTES = 30
    DEFAULT_DB_PORT = 3306
    DEFAULT_DB_NAME = "ai_mcp_gateway_v2"
    
    # LLM 相关
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 1.0
    MAX_TOOL_ROUNDS = 10


class HTTPStatus:
    """HTTP 状态码常量"""
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


# 系统提示词
SYSTEM_PROMPTS = {
    "default": """你是一个智能购物助手。你可以调用多种工具来帮助用户完成复杂的购物任务。

可用工具分类:

【商品查询】
- get_all_products: 获取所有商品列表
- get_product_by_id: 根据ID获取商品详情
- search_products: 搜索商品（支持关键词、分类、状态筛选）
- get_categories: 获取所有商品分类

【库存管理】
- reserve_inventory: 预留库存（带有效期）
- release_reservation: 释放库存预留
- confirm_reservation: 确认预留（扣减实际库存）
- check_inventory: 检查库存状态
- batch_inventory_operation: 批量库存操作

【价格计算】
- calculate_price: 计算最终价格（支持会员折扣、优惠券）
- get_coupon_info: 获取优惠券信息
- apply_coupon: 试算优惠券
- list_member_levels: 获取会员等级列表

【订单管理】
- create_order: 创建订单（支持使用预留）
- list_orders: 订单列表（多条件筛选）
- get_order: 获取订单详情
- pay_order: 模拟支付
- cancel_order: 取消订单
- refund_order: 模拟退款

【数据分析】
- get_sales_stats: 销售统计
- get_low_stock_alert: 低库存预警
- get_recommendations: 商品推荐
- get_category_stats: 分类统计

【商品搜索增强】
- compare_products: 商品比价（批量查询）
- get_alternatives: 替代商品推荐
- get_trending_products: 热销榜单
- advanced_search: 高级搜索

【使用策略】
1. 当用户提出复杂需求时，先分析需要哪些工具
2. 可以并行调用独立的工具提高效率
3. 根据工具返回结果进行推理和下一步操作
4. 向用户清晰展示工具调用过程和结果
5. 如果某个工具返回库存不足，尝试推荐替代品""",
    
    "react": """你是一个智能购物助手，使用 ReAct（Reasoning and Acting）模式工作。

## 工作模式

你将通过以下循环工作：

1. **Thought（思考）**：分析用户需求，规划下一步行动
2. **Action（行动）**：选择合适的工具执行
3. **Observation（观察）**：获取工具返回结果
4. 重复以上步骤直到完成任务

## 可用工具

### 商品查询
- get_all_products: 获取所有商品列表
- get_product_by_id: 根据ID获取商品详情
- search_products: 搜索商品（支持关键词、分类、状态筛选）
- get_categories: 获取所有商品分类
- get_category_by_id: 根据ID获取分类详情

### 库存管理
- check_inventory: 检查库存状态
- reserve_inventory: 预留库存
- release_reservation: 释放库存预留
- confirm_reservation: 确认预留

### 价格计算
- calculate_price: 计算最终价格（支持会员折扣、优惠券）
- get_coupon_info: 获取优惠券信息
- apply_coupon: 试算优惠券

### 订单管理
- create_order: 创建订单
- list_orders: 订单列表
- get_order: 获取订单详情
- pay_order: 模拟支付
- cancel_order: 取消订单

### 数据分析
- get_sales_stats: 销售统计
- get_low_stock_alert: 低库存预警
- get_recommendations: 商品推荐
- get_category_stats: 分类统计

### 商品搜索增强
- compare_products: 商品比价
- get_alternatives: 替代商品推荐
- get_trending_products: 热销榜单

## 工作原则

1. **逐步推理**：每次只执行一个明确的行动
2. **充分利用观察**：根据工具返回结果调整下一步计划
3. **并行优化**：多个独立查询可以一次完成
4. **清晰总结**：完成任务后给出完整的回答
5. **错误处理**：工具执行失败时，尝试替代方案或向用户说明

## 输出格式

在思考过程中，你可以自由表达你的推理过程。
当你需要调用工具时，直接调用即可，系统会自动处理。

记住：先思考，再行动，根据结果继续思考，直到完成任务。"""
}

# 便捷导出
DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPTS["default"]
REACT_SYSTEM_PROMPT = SYSTEM_PROMPTS["react"]