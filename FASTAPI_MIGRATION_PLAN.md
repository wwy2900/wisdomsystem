# FastAPI 改造计划

## 1. 概要

将项目从“Streamlit 直接调用 Agent”的结构，改造成“FastAPI 后端 + Streamlit 演示前端共存”的结构。

第一版目标：

- 使用 FastAPI 提供正式后端接口。
- 使用 SSE（Server-Sent Events）提供聊天流式输出。
- 使用简单 API Key 保护业务接口。
- 保留现有 `ReactAgent`、RAG、记忆系统、会话文件能力。
- 保留 `app.py` 作为本地演示界面，后续可逐步改为调用 FastAPI。

---

## 2. 核心改造内容

### 2.1 新增依赖

在 `requirements.txt` 中新增：

```txt
fastapi
uvicorn[standard]
```

### 2.2 新增 FastAPI 后端模块

建议新增以下目录和文件：

```text
api/
  __init__.py
  main.py
  schemas.py
  dependencies.py
  routes/
    __init__.py
    chat.py

services/
  __init__.py
  chat_service.py
```

职责划分：

| 文件 | 职责 |
| --- | --- |
| `api/main.py` | 创建 FastAPI app、注册路由、健康检查、启动生命周期 |
| `api/schemas.py` | 定义 Pydantic 请求/响应模型 |
| `api/dependencies.py` | API Key 校验、服务实例获取 |
| `api/routes/chat.py` | 聊天、会话、历史接口 |
| `services/chat_service.py` | 统一封装 `ReactAgent`、`SessionManager`、`RedisCache` |

### 2.3 新增服务层

新增 `ChatService`，统一封装聊天业务逻辑。

该服务负责：

- 初始化并持有 `ReactAgent`、`SessionManager`、`RedisCache`。
- 创建会话。
- 读取历史会话。
- 调用 `ReactAgent.execute_stream()`。
- 区分最终回答和工具调用过程。
- 在回答结束后保存会话。

这样可以避免 Streamlit 和 FastAPI 各自维护一套会话逻辑。

---

## 3. FastAPI 接口设计

### 3.1 健康检查

```http
GET /health
```

返回内容：

```json
{
  "status": "ok",
  "agent_ready": true,
  "cache_backend": "redis"
}
```

说明：

- `/health` 可不鉴权。
- 用于部署探活、启动验证和故障排查。

### 3.2 创建会话

```http
POST /api/v1/sessions
```

请求：

```json
{
  "user_id": "1001"
}
```

返回：

```json
{
  "session_id": "session_..."
}
```

### 3.3 查询用户历史会话

```http
GET /api/v1/users/{user_id}/sessions
```

返回：

```json
{
  "sessions": [
    {
      "session_id": "session_...",
      "preview": "最近一条消息预览",
      "saved_at": "2026-06-20T15:00:00"
    }
  ]
}
```

### 3.4 查询单个会话

```http
GET /api/v1/sessions/{session_id}
```

返回：

```json
{
  "session_id": "session_...",
  "user_id": "1001",
  "messages": [
    {
      "role": "user",
      "content": "机器人不回充怎么办？"
    },
    {
      "role": "assistant",
      "content": "可以先检查回充座供电..."
    }
  ]
}
```

如果会话不存在，返回 `404`。

### 3.5 普通聊天接口

```http
POST /api/v1/chat
```

请求：

```json
{
  "user_id": "1001",
  "session_id": "session_...",
  "message": "扫地机器人不回充怎么办？"
}
```

返回：

```json
{
  "session_id": "session_...",
  "answer": "可以先检查回充座供电、机器人底部触点..."
}
```

说明：

- 等待完整回答后一次性返回。
- 适合测试、脚本调用和不需要流式体验的客户端。

### 3.6 SSE 流式聊天接口

```http
POST /api/v1/chat/stream
```

请求：

```json
{
  "user_id": "1001",
  "session_id": "session_...",
  "message": "帮我生成这个月的使用报告"
}
```

响应类型：

```http
Content-Type: text/event-stream
```

事件格式：

```text
event: answer_delta
data: {"content": "可以"}

event: answer_delta
data: {"content": "，我来帮你生成使用报告。"}

event: tool_event
data: {"content": "fetch_external_data(user_id=1001, month=2026-06)"}

event: done
data: {"session_id": "session_..."}
```

事件类型：

| 事件 | 说明 |
| --- | --- |
| `answer_delta` | 最终回答片段 |
| `tool_event` | 工具调用、工具返回或中间过程 |
| `done` | 回答完成 |
| `error` | 异常信息 |

---

## 4. API Key 鉴权方案

第一版使用简单 API Key。

### 4.1 环境变量

新增：

```env
FASTAPI_API_KEY=your_api_key_here
```

### 4.2 请求头

客户端请求 `/api/v1/*` 接口时带上：

```http
X-API-Key: your_api_key_here
```

### 4.3 鉴权规则

- `/health` 不需要鉴权。
- `/api/v1/*` 默认需要鉴权。
- API Key 缺失或错误时返回 `401 Unauthorized`。
- 不在日志中打印完整 API Key。

---

## 5. 启动生命周期设计

FastAPI 使用 `lifespan` 初始化重型组件。

启动时初始化：

- `RedisCache()`
- `SessionManager()`
- `ReactAgent()`
- `ChatService()`

将服务对象挂载到：

```python
app.state.chat_service
```

路由中通过依赖函数获取：

```python
request.app.state.chat_service
```

这样可以避免每个请求重复初始化 Agent、模型、RAG 和数据库连接。

---

## 6. Streamlit 后续调整

第一阶段保留现有 `app.py` 直接调用本地服务。

第二阶段可以将 `app.py` 调整为 FastAPI 客户端：

- 用户输入后调用 `POST /api/v1/chat/stream`。
- 使用 SSE 接收回答片段。
- Streamlit 只负责展示 UI，不再直接持有 `ReactAgent`。

最终结构：

```text
前端 UI / 第三方系统
        ↓
FastAPI
        ↓
ChatService
        ↓
ReactAgent + RAG + Memory
```

---

## 7. 测试计划

### 7.1 单元测试

建议覆盖：

- API Key 缺失返回 `401`。
- API Key 错误返回 `401`。
- 创建会话返回合法 `session_id`。
- 查询不存在会话返回 `404`。
- `ChatService` 能保存用户消息和 assistant 回答。

### 7.2 集成测试

建议覆盖：

- `GET /health` 返回正常状态。
- `POST /api/v1/chat` 能返回完整回答。
- `POST /api/v1/chat/stream` 能输出 `answer_delta` 和 `done` 事件。
- 原有 `streamlit run app.py` 仍可启动。
- 原有 RAG 评测脚本仍可运行。

### 7.3 编译检查

建议执行：

```bash
python -m compileall agent memory rag database utils model api services tests app.py
```

---

## 8. README 更新内容

README 中建议新增 FastAPI 启动方式：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

访问接口文档：

```text
http://localhost:8000/docs
```

健康检查：

```bash
curl http://localhost:8000/health
```

普通聊天示例：

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d "{\"user_id\":\"1001\",\"message\":\"扫地机器人不回充怎么办？\"}"
```

---

## 9. 实施顺序

建议按以下顺序推进：

1. 新增 FastAPI 和 uvicorn 依赖。
2. 新增 `ChatService`，把聊天、会话保存逻辑从 `app.py` 中抽出。
3. 新增 `api/main.py`、`api/schemas.py`、`api/dependencies.py`。
4. 新增会话接口和普通聊天接口。
5. 新增 SSE 流式聊天接口。
6. 增加 API Key 鉴权。
7. 增加测试。
8. 更新 README。
9. 可选：将 Streamlit 改为调用 FastAPI。

---

## 10. 默认假设

- 第一版不移除 Streamlit。
- 第一版使用 SSE，不使用 WebSocket。
- 第一版使用简单 API Key，不做 JWT 登录。
- FastAPI 只做服务化封装，不重写现有 Agent、RAG、记忆逻辑。
- 后续如果需要正式多用户系统，再扩展登录、JWT、权限和用户隔离。

