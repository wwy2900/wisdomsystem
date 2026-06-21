# 项目后续优化与功能扩展建议

## 1. 概要

项目已经完成 FastAPI 封装，当前具备 Streamlit 演示入口、FastAPI 后端接口、Agent 对话、RAG 检索、记忆系统、会话管理和基础 SSE 流式输出能力。

下一阶段建议从“能跑”升级到“可用、可测、可上线”，重点补齐以下能力：

- FastAPI 服务健康状态真实化。
- API 鉴权、错误响应、请求追踪和限流。
- 会话 ID、会话恢复和历史索引稳定性。
- SSE 流式接口的非阻塞化。
- API 层自动化测试。
- 知识库、故障诊断、使用报告、工单等业务模块。

---

## 2. P0：优先工程优化

### 2.1 健康检查改为真实状态

当前 `/health` 建议避免硬编码 `agent_ready=True`、`cache_backend="redis"`。

建议返回真实状态：

- `agent_ready`：`ChatService` 和 `ReactAgent` 是否初始化成功。
- `cache_backend`：实际使用 `redis` 还是 `simple_cache`。
- `redis_available`：Redis 是否可用。
- `model_key_configured`：`DASHSCOPE_API_KEY` 是否配置。
- `vector_store_ready`：Chroma 向量库是否可访问。

示例：

```json
{
  "status": "ok",
  "agent_ready": true,
  "cache_backend": "redis",
  "redis_available": true,
  "model_key_configured": true,
  "vector_store_ready": true
}
```

验收标准：

- Redis 不可用时能返回 `cache_backend=simple_cache`。
- 模型 Key 缺失时能明确暴露配置异常。
- 部署探活可以通过 `/health` 判断服务是否可用。

### 2.2 API Key 策略收紧

当前如果 `FASTAPI_API_KEY` 未配置，接口可能直接放行。开发环境可以接受，但生产环境不安全。

建议：

- 默认必须配置 `FASTAPI_API_KEY`。
- 如果确实要关闭鉴权，必须显式设置 `FASTAPI_AUTH_DISABLED=true`。
- 日志中不要打印完整 API Key。
- README 中明确开发和生产的鉴权配置差异。

验收标准：

- 未配置 `FASTAPI_API_KEY` 且未显式关闭鉴权时，服务启动或请求应给出明确错误。
- `/health` 可保持不鉴权。
- `/api/v1/*` 默认需要 `X-API-Key`。

### 2.3 会话 ID 改为 UUID 或毫秒级唯一 ID

当前会话 ID 如果仍使用秒级时间戳，同一秒多个请求可能冲突。

建议格式：

```text
session_20260620_223455_ab12cd
```

或：

```text
session_550e8400-e29b-41d4-a716-446655440000
```

验收标准：

- 同一秒连续创建多个会话不会覆盖。
- 旧会话文件仍可读取。
- 会话文件名安全，不包含路径穿越字符。

### 2.4 聊天接口允许自动创建会话

当前 `ChatRequest.session_id` 建议改为可选。

行为建议：

- 如果请求带 `session_id`，使用现有会话。
- 如果请求不带 `session_id`，自动创建新会话。
- 响应始终返回实际使用的 `session_id`。

示例请求：

```json
{
  "user_id": "1001",
  "message": "扫地机器人不回充怎么办？"
}
```

示例响应：

```json
{
  "session_id": "session_...",
  "answer": "可以先检查回充座供电..."
}
```

验收标准：

- 第三方系统可以不先调用创建会话接口，直接调用聊天接口。
- SSE 接口和普通聊天接口行为一致。

### 2.5 SSE 流式接口非阻塞化

如果 FastAPI 的 async endpoint 中直接遍历同步 Agent 生成器，长时间模型调用可能阻塞事件循环。

建议：

- 使用线程池桥接同步生成器。
- 或将 `ChatService` 流式逻辑封装为 async generator。
- 对客户端断开连接进行处理，避免后台继续无意义生成。

验收标准：

- 一个慢请求不会阻塞其他健康检查或普通请求。
- SSE 客户端断开时服务能停止后续输出或安全清理。
- 流式事件保持 `answer_delta`、`tool_event`、`done`、`error` 格式稳定。

### 2.6 补齐 FastAPI 自动化测试

建议新增 API 层测试，覆盖最小关键路径。

测试场景：

- `GET /health` 返回正常状态。
- API Key 缺失返回 `401`。
- API Key 错误返回 `401`。
- 创建会话返回合法 `session_id`。
- 查询不存在会话返回 `404`。
- `/api/v1/chat` 返回 `answer` 和 `session_id`。
- `/api/v1/chat/stream` 返回 `answer_delta` 和 `done` 事件。

验收标准：

- 本地一条命令可运行 API 测试。
- 测试中应 mock 或替换真实模型调用，避免依赖外部 LLM。

---

## 3. P1：服务化与可观测性优化

### 3.1 统一错误响应格式

建议所有接口错误统一为：

```json
{
  "code": "SESSION_NOT_FOUND",
  "message": "Session not found",
  "request_id": "req_..."
}
```

常见错误码：

| code | 场景 |
| --- | --- |
| `INVALID_API_KEY` | API Key 缺失或错误 |
| `SESSION_NOT_FOUND` | 会话不存在 |
| `VALIDATION_ERROR` | 请求参数错误 |
| `AGENT_ERROR` | Agent 执行失败 |
| `TOOL_ERROR` | 工具调用失败 |
| `RATE_LIMITED` | 请求被限流 |

### 3.2 增加 request_id 中间件

建议每个请求生成或透传 `X-Request-ID`。

用途：

- 关联接口响应、服务日志、模型调用日志和工具调用日志。
- 排查线上问题。
- 后续接入链路追踪。

验收标准：

- 响应头包含 `X-Request-ID`。
- 日志中包含对应 request_id。
- SSE 的 `error` 事件包含 request_id。

### 3.3 增加 CORS 配置

如果后续前端独立部署，需要 CORS。

建议新增环境变量：

```env
FASTAPI_CORS_ORIGINS=http://localhost:3000,http://localhost:8501
```

验收标准：

- 开发环境允许本地前端访问。
- 生产环境只允许明确配置的域名。

### 3.4 增加输入限制与限流

建议补齐：

- 单条消息最大长度。
- 单用户每分钟请求数。
- 单 IP 每分钟请求数。
- 单会话最大历史长度。

验收标准：

- 超长输入返回明确错误。
- 高频请求返回 `429`。
- 不影响正常 SSE 输出。

### 3.5 Redis 配置读取与降级日志

建议 `RedisCache` 从环境变量或配置文件读取：

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

同时记录：

- Redis 连接成功。
- Redis 连接失败并降级到 `SimpleCache`。
- 当前缓存后端。

验收标准：

- `/health` 能看到实际缓存后端。
- 日志清楚说明是否降级。

---

## 4. P2：架构与部署优化

### 4.1 Streamlit 改为 FastAPI 客户端

当前 Streamlit 如果仍直接持有 `ReactAgent`，会导致 UI 与后端业务逻辑重复。

建议后续改造为：

```text
Streamlit UI
    ↓ HTTP/SSE
FastAPI
    ↓
ChatService
    ↓
ReactAgent + RAG + Memory
```

收益：

- UI 和后端解耦。
- 第三方系统接入路径一致。
- 更容易部署为前后端分离架构。

### 4.2 Docker 与 Compose

建议新增：

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

服务建议：

- `api`：FastAPI 服务。
- `redis`：缓存服务。
- `streamlit`：可选演示 UI。

验收标准：

- 一条命令启动 API 和 Redis。
- 环境变量通过 `.env` 注入。
- 日志、数据、向量库目录挂载清晰。

### 4.3 CI 检查

建议接入最小 CI：

- `python -m compileall`
- `pytest`
- 依赖安装检查。
- 密钥扫描。
- RAG 评测可作为手动或定时任务。

验收标准：

- PR 或提交前能发现语法错误和基础接口回归。
- 不把 `.env`、数据库、日志、向量库提交到仓库。

---

## 5. 可新增业务模块

### 5.1 知识库管理模块

目标：让运维或客服人员可以维护 RAG 知识库。

功能建议：

- 上传文档。
- 查看文档列表。
- 查看 chunk 内容。
- 重建向量库。
- 删除文档。
- 查看检索命中来源。
- 查看文档 MD5 去重状态。

接口建议：

- `POST /api/v1/knowledge/documents`
- `GET /api/v1/knowledge/documents`
- `GET /api/v1/knowledge/chunks`
- `POST /api/v1/knowledge/rebuild`
- `DELETE /api/v1/knowledge/documents/{doc_id}`

### 5.2 故障诊断模块

目标：把扫地机器人故障排查做成结构化多轮流程。

功能建议：

- 收集设备型号。
- 收集错误码。
- 收集故障现象。
- 收集使用环境。
- 记录已尝试方案。
- 输出排查步骤。
- 无法解决时建议转人工或生成工单。

适合场景：

- 不回充。
- 卡住。
- 吸力下降。
- 不出水。
- 地图异常。
- 异响。
- 耗材提醒。

### 5.3 使用报告模块

当前已有外部使用数据读取基础，可以扩展为正式报告模块。

报告内容建议：

- 清扫面积和频次。
- 清扫效率趋势。
- 耗材状态。
- 异常次数。
- 维护建议。
- 同类用户对比。
- 下月使用建议。

接口建议：

- `POST /api/v1/reports/monthly`
- `GET /api/v1/reports/{report_id}`
- `GET /api/v1/users/{user_id}/reports`

### 5.4 工单模块

目标：Agent 不能解决时，生成可交给人工客服的工单。

工单字段建议：

- 工单 ID。
- 用户 ID。
- 会话 ID。
- 问题摘要。
- 已尝试方案。
- RAG 引用资料。
- 工具调用记录。
- 建议优先级。
- 当前状态。

接口建议：

- `POST /api/v1/tickets`
- `GET /api/v1/tickets/{ticket_id}`
- `PATCH /api/v1/tickets/{ticket_id}`

### 5.5 用户与设备档案模块

目标：让回答更个性化。

建议记录：

- 用户绑定设备。
- 设备型号。
- 购买时间。
- 耗材更换时间。
- 家庭面积。
- 是否有宠物。
- 常见故障。
- 用户偏好。

接口建议：

- `GET /api/v1/users/{user_id}/profile`
- `PATCH /api/v1/users/{user_id}/profile`
- `POST /api/v1/users/{user_id}/devices`
- `GET /api/v1/users/{user_id}/devices`

### 5.6 反馈与评测模块

目标：收集真实用户反馈，反哺 RAG 和提示词优化。

建议记录：

- 用户问题。
- Agent 回答。
- 检索命中文档。
- 工具调用轨迹。
- 点赞/点踩。
- 用户补充反馈。
- 是否转人工。

接口建议：

- `POST /api/v1/feedback`
- `GET /api/v1/feedback/stats`

### 5.7 运营分析后台

目标：帮助团队发现高频问题和系统瓶颈。

指标建议：

- 高频问题。
- RAG 未命中问题。
- 工具调用成功率。
- 平均响应时间。
- 首 token 延迟。
- 转人工率。
- 用户满意度。
- 模型调用失败率。

---

## 6. 推荐实施顺序

### 第一阶段：FastAPI 稳定性

1. 健康检查真实化。
2. 会话 ID 改为唯一 ID。
3. `ChatRequest.session_id` 改为可选。
4. API Key 策略收紧。
5. SSE 非阻塞化。
6. 补 API 自动化测试。

### 第二阶段：可观测性与安全

1. 统一错误响应。
2. 增加 request_id。
3. 增加 CORS。
4. 增加输入长度限制。
5. 增加基础限流。
6. Redis 配置读取和降级日志。

### 第三阶段：业务模块

1. 知识库管理模块。
2. 故障诊断模块。
3. 使用报告模块。
4. 工单模块。
5. 用户与设备档案模块。
6. 反馈与评测模块。

### 第四阶段：部署与运营

1. Streamlit 改为 FastAPI 客户端。
2. Docker / docker-compose。
3. CI 检查。
4. 运营分析后台。
5. RAG 评测历史对比。

---

## 7. 总结

当前项目已经完成 FastAPI 基础封装，下一步不建议立刻堆大量业务功能，而应优先补齐服务稳定性和可测试性。

最推荐优先落地的 5 项：

1. `/health` 返回真实服务状态。
2. 会话 ID 改为唯一 ID。
3. 聊天接口支持自动创建会话。
4. SSE 流式接口非阻塞化。
5. 增加 FastAPI 自动化测试。

这几项完成后，再扩展知识库管理、故障诊断、使用报告、工单和用户设备档案，会更稳、更容易维护。

