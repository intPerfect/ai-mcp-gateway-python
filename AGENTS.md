# AI MCP Gateway 项目指南

## 项目概览

本项目是一个 **MCP (Model Context Protocol) 网关系统**，用于将 HTTP API 动态转换为 MCP 工具，供 LLM Agent 调用。

### 项目结构

```
ai-mcp-gateway/
├── ai-mcp-gateway-python/    # Python 网关后端 (主项目)
├── ai-mcp-gateway-vue/       # Vue 前端管理界面
└── product-service/          # 测试用 HTTP 服务 (模拟商品服务)
```

---

## 数据库配置

- **Host**: localhost:3306
- **User**: root
- **Password**: 123456
- **Database**: ai_mcp_gateway_v2

### 重要规则

1. **直接修改最终 SQL**: 对库表结构的修改，直接同步到 `scripts/init_db.sql`，不需要写增量脚本
2. **不需要保留本地数据**: 表结构变更时直接刷库即可
3. **ORM 模型同步**: 修改表结构后，需同步更新 `app/infrastructure/database/models.py`

### 核心表结构

| 表名 | 说明 |
|------|------|
| `mcp_gateway` | 网关配置表 |
| `mcp_gateway_auth` | API Key 认证表 |
| `mcp_gateway_tool` | MCP 工具配置表 |
| `mcp_protocol_http` | HTTP 协议配置表 |
| `mcp_protocol_mapping` | 参数映射配置表 (核心) |

---

## Python 网关分包结构

```
app/
├── api/                    # API 层 - 接口路由
│   ├── routers/           # 路由模块
│   │   ├── chat.py        # WebSocket 对话路由
│   │   ├── tools.py       # 工具管理路由
│   │   ├── openapi.py     # OpenAPI 导入路由
│   │   ├── apikeys.py     # API Key 管理路由
│   │   └── mcp_gateway.py # MCP SSE 路由
│   ├── schemas/           # 请求/响应模型
│   └── dependencies.py    # FastAPI 依赖注入
│
├── application/           # 应用层 - 用例编排
│   ├── chat/              # 对话应用服务
│   ├── tool/              # 工具应用服务
│   └── llm/               # LLM 应用服务
│
├── domain/                # 领域层 - 核心业务逻辑
│   ├── agent/             # Agent 领域 (ReAct 模式)
│   ├── chat/              # 对话领域 (消息历史管理)
│   ├── tool/              # 工具领域 (工具注册表)
│   ├── auth/              # 认证领域
│   ├── session/           # 会话管理
│   └── protocol/          # 协议解析
│       └── openapi/       # OpenAPI 规范解析
│
├── infrastructure/        # 基础设施层
│   ├── database/          # 数据库
│   │   ├── connection.py  # 连接管理
│   │   ├── models.py      # ORM 模型
│   │   └── repository.py  # 数据仓库
│   ├── logging/           # 日志服务
│   └── utils/             # 工具函数
│
├── services/              # 服务层 (待重构迁移)
│   ├── llm_service.py     # LLM 调用服务
│   ├── react_agent.py     # ReAct Agent 实现
│   └── mcp_tool_registry.py # 工具注册
│
├── core/                  # 核心配置
│   └── container.py       # 依赖注入容器
│
├── config.py              # 应用配置
├── constants.py           # 常量定义
└── main.py                # 应用入口
```

### 分层职责

| 层级 | 职责 | 示例 |
|------|------|------|
| API | 接收请求、参数校验、响应格式化 | routers/chat.py |
| Application | 用例编排、协调领域服务 | chat/chat_service.py |
| Domain | 核心业务逻辑、领域模型 | agent/service.py, tool/registry.py |
| Infrastructure | 技术实现细节 | database/, logging/ |
| Services | 历史服务层 (逐步迁移至 domain/application) | llm_service.py |

---

## Vue 前端结构

```
src/
├── api/           # API 请求封装
├── components/    # 公共组件
├── constants/     # 常量定义
├── hooks/         # Vue Hooks
├── router/        # 路由配置
├── stores/        # Pinia 状态管理
├── types/         # TypeScript 类型定义
├── utils/         # 工具函数
└── views/         # 页面组件
```

---

## Product Service (测试服务)

模拟商品管理的 HTTP 服务，用于测试 MCP 工具调用。

- **端口**: 5000
- **功能**: 商品 CRUD、分类管理、订单管理

### OpenAPI 导入

可通过以下接口导入工具配置：
```
POST /openapi/import
{
  "gateway_id": "gateway_001",
  "service_name": "product-service",
  "service_url": "http://localhost:5000",
  "openapi_url": "http://localhost:5000/openapi.json"
}
```

---

## 运行命令

### Python 网关

```bash
cd ai-mcp-gateway-python
uv sync                    # 安装依赖
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Vue 前端

```bash
cd ai-mcp-gateway-vue
npm install
npm run dev
```

### Product Service

```bash
cd product-service
uv sync
uv run python main.py
```

---

## 关键技术点

### 1. MCP 工具动态注册

工具配置存储在数据库中，启动时从数据库加载并动态注册：
- `mcp_gateway_tool` 定义工具名称、描述
- `mcp_protocol_http` 定义 HTTP 调用方式
- `mcp_protocol_mapping` 定义参数映射规则

### 2. ReAct Agent 模式

Agent 采用 ReAct (Reasoning and Acting) 模式：
1. **Thought**: 分析用户意图，决定下一步行动
2. **Action**: 调用 MCP 工具
3. **Observation**: 观察工具返回结果
4. 循环直到完成任务

### 3. 参数映射

支持多种 HTTP 参数位置：
- `path`: 路径参数，替换 URL 中的 `{param}`
- `query`: 查询参数
- `body`: JSON 请求体
- `header`: HTTP 头部
- `form`: 表单数据
- `file`: 文件上传

### 4. API Key 职责分离

系统使用两种 API Key：
- **Gateway API Key**: 用于访问 MCP 网关 (存储在 `mcp_gateway_auth`)
- **LLM API Key**: 用于调用 LLM 服务 (配置在 `.env`)

---

## 常见任务

### 添加新工具

1. 在数据库中插入工具配置
2. 重启服务或调用 `/tools/reload` 接口

### 修改表结构

1. 修改 `scripts/init_db.sql`
2. 同步修改 `app/infrastructure/database/models.py`
3. 刷库后重启服务

### 调试对话

对话日志存储在 `app/logs/conversations/` 目录，按日期分目录，每个会话一个 `.jsonl` 文件。
