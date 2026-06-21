# Agent 系统关键说明

本文档记录“智扫通·智能客服”项目中 Agent、FastAPI、RAG、记忆和知识库管理的核心维护信息。详细变更和规划见 `README.md`、`PROJECT_IMPROVEMENT_PLAN.md`、`NEXT_OPTIMIZATION_AND_FEATURE_PLAN.md`。

---

## 1. 系统架构

项目采用分层结构：

| 层级 | 说明 | 关键文件 |
| --- | --- | --- |
| 用户界面层 | Streamlit 聊天页和知识库管理页 | `app.py` |
| API 服务层 | FastAPI 后端、鉴权、SSE 流式接口 | `api/main.py`, `api/routes/` |
| 服务层 | 封装聊天和知识库业务逻辑 | `services/chat_service.py`, `services/knowledge_service.py` |
| Agent 层 | ReAct Agent 推理、工具调用、流式输出 | `agent/react_agent.py` |
| 工具层 | RAG、天气、用户信息、外部数据、报告触发 | `agent/tools/agent_tools.py` |
| 记忆层 | L1-L4 四层记忆、用户画像、会话摘要 | `memory/` |
| RAG 层 | 向量检索、BM25、Query 改写、Rerank | `rag/` |
| 存储层 | Redis/SimpleCache、SQLite、ChromaDB | `database/`, `chroma_db/` |

---

## 2. 核心组件

| 组件 | 职责 | 文件 |
| --- | --- | --- |
| `ReactAgent` | 核心智能体，负责对话推理、工具调用和流式输出 | `agent/react_agent.py` |
| `ChatService` | FastAPI 和上层调用复用的聊天服务 | `services/chat_service.py` |
| `KnowledgeService` | 知识库上传、检索、删除、重建服务 | `services/knowledge_service.py` |
| `MemoryManager` | 四层记忆统一入口 | `memory/memory_manager.py` |
| `RagSummarizeService` | RAG 检索和摘要生成 | `rag/rag_service.py` |
| `VectorStoreService` | ChromaDB 向量库操作和知识库 chunk 管理 | `rag/vector_store.py` |
| `RedisCache` | Redis 缓存，失败时降级到内存缓存 | `database/redis_cache.py` |
| `SessionManager` | 会话创建、保存、加载和历史列表 | `memory/session_manager.py` |

核心组件大多采用单例或服务封装，目的是避免重复初始化模型、向量库、数据库连接等重型资源。

---

## 3. FastAPI 接口

FastAPI 入口：`api/main.py`

启动命令：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档：

```text
http://localhost:8000/docs
```

### 聊天与会话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| POST | `/api/v1/sessions` | 创建会话 |
| GET | `/api/v1/users/{user_id}/sessions` | 查询用户历史会话 |
| GET | `/api/v1/sessions/{session_id}` | 查询会话详情 |
| POST | `/api/v1/chat` | 非流式聊天 |
| POST | `/api/v1/chat/stream` | SSE 流式聊天 |

### 知识库管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/knowledge/documents/upload` | 上传 `.txt` / `.pdf` 并立即入库 |
| GET | `/api/v1/knowledge/chunks` | 分页查看 chunk |
| GET | `/api/v1/knowledge/search` | 检索预览 |
| DELETE | `/api/v1/knowledge/chunks/{doc_id}` | 删除指定 chunk，不删除原始文件 |
| POST | `/api/v1/knowledge/rebuild` | 清空并重建索引 |

除 `/health` 外，业务接口复用 `X-API-Key` 鉴权，密钥来自 `FASTAPI_API_KEY`。

---

## 4. Agent 工具

当前 Agent 工具：

| 工具 | 说明 |
| --- | --- |
| `rag_summarize` | 从向量库检索资料并生成摘要 |
| `get_weather` | 返回指定城市天气信息 |
| `get_user_location` | 返回用户城市，当前为默认值 |
| `get_user_id` | 返回用户 ID，当前为默认值 |
| `get_current_month` | 返回当前月份，格式 `YYYY-MM` |
| `fetch_external_data` | 从 CSV 获取用户使用记录，返回 JSON 字符串 |
| `fill_context_for_report` | 触发报告生成上下文注入 |

工具约束：

- 使用 `@tool` 注册。
- 参数必须有类型注解。
- 返回值统一为字符串。
- 复杂结构返回 JSON 字符串。
- 工具内部捕获异常并记录日志。

---

## 5. 记忆与 RAG

### 四层记忆

| 层级 | 类型 | 存储 |
| --- | --- | --- |
| L1 | 当前对话上下文 | Redis / SimpleCache |
| L2 | 用户画像 | SQLite + Redis |
| L3 | 近期摘要 | SQLite + Redis |
| L4 | 长期经验 | RAG 向量库 |

### RAG 流程

```text
用户问题
→ Query 改写
→ 语义校验
→ 向量检索 + BM25 检索
→ RRF 融合
→ Rerank 精排
→ 生成回答
```

知识库文件默认来自：

- `data/`
- `data/knowledge_uploads/`

上传目录已加入 `.gitignore`，避免误提交用户上传资料。

---

## 6. 配置与依赖

核心配置：

| 配置 | 说明 |
| --- | --- |
| `DASHSCOPE_API_KEY` | 通义千问 API Key，必填 |
| `FASTAPI_API_KEY` | FastAPI 业务接口鉴权密钥 |
| `REDIS_HOST` | Redis 地址 |
| `REDIS_PORT` | Redis 端口 |
| `REDIS_DB` | Redis DB |

关键依赖：

| 依赖 | 用途 |
| --- | --- |
| `langchain`, `langgraph` | Agent 和工作流 |
| `langchain-chroma`, `chromadb` | 向量库 |
| `streamlit` | Web 演示和管理页 |
| `fastapi`, `uvicorn` | API 后端 |
| `sse-starlette` | SSE 流式响应 |
| `python-multipart` | 文件上传 |
| `dashscope` | 通义千问模型 |
| `redis` | 缓存 |
| `rank_bm25`, `jieba`, `numpy` | RAG 检索和排序 |

---

## 7. 启动方式

项目默认 Conda 环境：

```bash
conda activate wisdomsystem-py311
```

Streamlit：

```bash
conda activate wisdomsystem-py311
streamlit run app.py --server.port 8501
```

FastAPI：

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

RAG 评估：

```bash
python tests/rag_evaluation.py
```

语法检查：

```bash
python -m compileall agent memory rag database utils model api services app.py tests
```

---

## 8. 扩展规则

### 新增 Agent 工具

1. 在 `agent/tools/agent_tools.py` 实现函数。
2. 使用 `@tool` 注册。
3. 在 `ReactAgent` 初始化时加入工具列表。
4. 保持返回值为字符串或 JSON 字符串。

### 新增 API

1. 在 `api/schemas.py` 定义模型。
2. 在 `services/` 实现业务逻辑。
3. 在 `api/routes/` 新增路由。
4. 在 `api/main.py` 注册路由和服务。
5. 复用 `verify_api_key` 做鉴权。

### 扩展知识库

1. 新文件类型先更新 `config/chroma.yml`。
2. 在 `VectorStoreService._get_file_documents()` 增加 loader。
3. 在 `KnowledgeService` 封装业务逻辑。
4. 破坏性操作必须在 UI 中提供确认。

---

## 9. 维护重点

优先关注：

- API Key 和模型 Key 不得硬编码。
- `.env`、日志、数据库、向量库和上传文件不得提交。
- RAG 修改后运行评估脚本。
- FastAPI 路由层只做参数和响应处理，业务逻辑放服务层。
- 知识库删除当前只删除 chunk，不删除原始文件。
- 重建索引会清空当前向量库，执行前需明确提示。

---

## 10. 版本记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1.0 | 初始版本 | 基础 Agent、对话和工具系统 |
| v1.1 | 2026-06-19 | 单例优化、系统消息冲突修复、性能优化 |
| v1.2 | 2026-06-19 | 安全修复、流式输出修复、CSV 解析、依赖补齐 |
| v1.3 | 2026-06-20 | FastAPI 服务层和知识库管理模块 |

**适用版本：** v1.3  
**最后更新：** 2026-06-20
