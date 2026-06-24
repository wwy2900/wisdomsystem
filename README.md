<div align="center">

# 🤖 智扫通 · 智能客服

**面向扫地机器人场景的 RAG 智能客服系统**

`FastAPI` + `Vue3` + `LangChain ReAct Agent` + `ChromaDB` + `BM25` + `Rerank`

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [项目架构](#项目架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [主要页面](#主要页面)
- [主要接口](#主要接口)
- [配置说明](#配置说明)
- [验证命令](#验证命令)
- [故障排除](#故障排除)
- [当前版本](#当前版本)

---

## 项目简介

`WisdomSystem` 是一个面向智能客服场景的 RAG 系统，核心能力包括：

- **聊天工作台**：SSE 流式回答、工具过程展示、历史会话切换
- **用户注册与管理**：登录页支持注册，管理员支持 `/admin/users` 创建和查看账号
- **私有知识隔离**：当前登录用户只能访问自己的会话和私有知识
- **管理员知识库**：共享知识上传、chunk 分页查看、检索预览、按 `doc_id` 删除、索引重建
- **客服业务工具**：设备档案、耗材状态、售后政策、服务渠道 4 类只读工具
- **答案来源展示**：assistant 消息支持折叠式 Sources 面板，展示知识库和业务工具来源
- **工具审计日志**：工具调用会写入 SQLite 摘要审计日志，记录用户、会话、工具名、状态、耗时和摘要
- **多格式入库**：`txt`、`pdf`、`docx`、`xlsx`、`csv`、`md`、`json`
- **PDF 结构化解析**：`Docling + OcrAutoOptions`
- **量化评测框架**：覆盖 RAG 检索、RAG 生成、Agent 工具选择、SSE 流式性能四类评测

---

## 核心特性

### 🔍 高级 RAG 检索

| 技术 | 说明 | 效果 |
|---|---|---|
| **Query 改写** | 三路改写：同义替换版、句式转换版、意图补全版 | 覆盖口语化/刁钻提问 |
| **语义校验** | 确保改写后的 Query 与原问题语义相似度 ≥ 0.8，避免偏离意图 | 过滤无效改写 |
| **BM25 混合召回** | 结合向量语义检索与 BM25 关键词匹配，使用 jieba 中文分词 | 兼顾语义和关键词 |
| **RRF 融合** | Reciprocal Rank Fusion 算法融合多源检索结果 | 优化排序结果 |
| **Rerank 精排** | 基于语义相似度的最终排序，支持批量嵌入计算 | 过滤无关文档 |
| **ContextualEnhancer** | 为每个 chunk 添加上下文描述（章节、主题、摘要），当前关闭以节省 token | Recall 提升（可选启用） |

**检索流程**：

```
用户提问 → 三路 Query 改写 → 语义校验过滤 → 向量检索 + BM25 检索 → RRF 融合 → Rerank 精排 → 返回 Top-5 文档
```

### 🧠 四层记忆库

| 层级 | 类型 | 存储方式 | 用途 |
|---|---|---|---|
| Layer 1 | 当前上下文 | Redis/本地缓存（截断式） | 短期对话上下文 |
| Layer 2 | 用户档案 | SQLite + Redis 缓存 | 用户姓名、职业、偏好等结构化信息 |
| Layer 3 | 对话摘要 | SQLite + Redis | 关键词提取、话题分类 |
| Layer 4 | 长期经验 | RAG 向量库 | 成功案例、失败尝试 |

### 💬 断点续聊

- 支持会话持久化存储（JSON 文件 + Redis）
- 跨会话记忆恢复，自动加载最近历史会话
- 用户画像自动更新
- 历史记录自动保存和加载

### 🛡️ 私有知识隔离

- RAG 检索范围固定为"共享知识库 + 当前用户私有知识"
- BM25 已补齐与向量检索一致的用户作用域语义
- 不会命中其他用户私有 chunk
- RAG 缓存 key 已带用户范围

### 📞 客服业务工具

| 工具 | 说明 | 数据来源 |
|---|---|---|
| `lookup_user_devices` | 查询用户设备档案 | SQLite |
| `lookup_device_consumables` | 查询设备耗材状态 | SQLite |
| `lookup_service_policy` | 查询售后政策 | `data/customer_support/` |
| `lookup_service_channels` | 查询服务渠道 | `data/customer_support/` |

### 📊 量化评测框架

| 评测类型 | 脚本 | 核心指标 |
|---|---|---|
| RAG 检索 | `eval/evaluate_retrieval.py` | Recall@1/3/5、MRR |
| RAG 生成 | `eval/evaluate_answer.py` | Keyword Coverage、Citation Rate、Answer Pass Rate、No-answer Accuracy |
| Agent 工具 | `eval/evaluate_agent.py` | Tool Selection Accuracy、First Tool Accuracy、Tool Success Rate、Source Rate |
| 流式性能 | `eval/benchmark_stream.py` | TTFT、Total Latency、P50/P95 |

### ⚡ 性能优化

| 优化项 | 效果 |
|---|---|
| 懒加载模型 | 首次调用时才初始化，避免启动时等待 |
| 查询缓存 | LRU + TTL，缓存命中时响应加速 |
| Redis 缓存降级 | Redis 连接失败时自动降级到本地内存缓存 |
| BM25 分词缓存 | 首次检索较慢，后续检索加速 |

---

## 项目架构

```text
用户界面层        Vue3 前端（登录页、聊天页、管理员知识库页、管理员用户页）
    ↓ HTTP/SSE
API 服务层        FastAPI 后端（Cookie 鉴权、角色权限、SSE 流式输出）
    ↓
服务层            聊天、知识库、认证、客服数据等业务封装
    ↓
Agent 层          ReAct Agent 推理、RAG 工具、客服业务工具
    ↓
记忆层            会话上下文、用户画像、会话摘要、长期经验
    ↓
RAG 层            文档解析、向量检索、BM25、Rerank、私有知识隔离
    ↓
存储层            Redis/SimpleCache、SQLite、ChromaDB、JSON 会话文件
```

---

## 技术栈

### 后端技术

| 技术 | 说明 |
|---|---|
| FastAPI | 高性能异步 Web 框架 |
| LangChain | 大语言模型应用开发框架（ReAct Agent + Tools） |
| LangGraph | Agent 编排 |
| ChromaDB | 轻量级向量数据库 |
| DashScope API | 大语言模型服务（通义千问） |
| rank_bm25 | 关键词检索（jieba 中文分词） |
| SQLite | 关系型数据库（用户、会话、客服数据、审计日志） |
| Redis / SimpleCache | 缓存（连接失败自动降级到内存缓存） |
| Docling | PDF 结构化解析与 OCR |
| sse-starlette | SSE 流式输出 |

### 前端技术

| 技术 | 说明 |
|---|---|
| Vue 3 | 现代化前端框架 |
| TypeScript | 类型安全 |
| Vite | 极速构建工具 |
| Pinia | 状态管理（authStore / sessionStore / chatStore / knowledgeStore） |
| Vue Router | 路由管理（路由守卫 + 角色权限） |
| Element Plus | UI 组件库 |
| @microsoft/fetch-event-source | SSE 客户端 |

### 部署

| 技术 | 说明 |
|---|---|
| Docker Compose | 单机部署主路径 |
| Docker Desktop + WSL2 | Windows 后端 |

---

## 项目结构

```text
wisdomsystem-main/
├── agent/                    # ReAct Agent 与工具
│   ├── tools/                # 工具定义（RAG 检索、客服业务工具）
│   └── react_agent.py        # ReAct Agent 实现（流式输出思考过程）
├── api/                      # FastAPI 后端
│   ├── main.py               # 应用入口
│   ├── routes/               # 路由（auth、me、admin、chat）
│   ├── dependencies.py       # 鉴权与依赖注入
│   └── schemas.py            # 请求/响应模型
├── config/                   # 配置文件
│   ├── agent.yml             # Agent 配置
│   ├── chroma.yml            # 向量库配置
│   ├── rag.yml               # RAG 配置
│   └── prompts.yml           # 提示词配置
├── data/                     # 本地数据
│   ├── customer_support/     # 客服结构化数据（售后政策、服务渠道）
│   ├── external/             # 外部数据
│   ├── sessions/             # 会话 JSON 文件
│   └── *.txt / *.pdf         # 知识库文档
├── database/                 # 数据库模块
│   ├── redis_cache.py        # Redis 缓存（降级到内存缓存）
│   └── sqlite_db.py          # SQLite 数据存储
├── eval/                     # 量化评测框架
│   ├── evaluate_retrieval.py # RAG 检索评测
│   ├── evaluate_answer.py    # RAG 生成评测
│   ├── evaluate_agent.py     # Agent 工具评测
│   ├── benchmark_stream.py   # SSE 流式性能评测
│   └── *.jsonl               # 评测数据集
├── memory/                   # 记忆管理
│   ├── layers.py             # 四层记忆定义
│   ├── memory_manager.py     # 记忆管理器
│   └── session_manager.py    # 会话管理（文件+Redis 持久化）
├── model/                    # 模型工厂
│   └── factory.py            # 通义千问模型初始化（懒加载）
├── prompts/                  # 提示词模板
├── rag/                      # RAG 检索模块
│   ├── rag_service.py        # RAG 服务入口
│   ├── vector_store.py       # 向量存储（ChromaDB + MD5 缓存）
│   ├── bm25_retriever.py     # BM25 检索（jieba 分词）
│   ├── query_rewriter.py     # Query 改写
│   ├── semantic_checker.py   # 语义相似度校验
│   ├── rrf_fusion.py         # RRF 融合算法
│   ├── reranker.py           # Rerank 精排
│   └── document_parser.py    # 多格式文档解析工厂
├── services/                 # 业务服务层
│   ├── chat_service.py       # 聊天服务
│   ├── knowledge_service.py  # 知识库服务
│   ├── auth_service.py       # 认证服务
│   └── customer_support_service.py  # 客服数据服务
├── utils/                    # 工具函数
├── web/                      # Vue3 前端
│   └── src/
│       ├── api/              # API 请求层
│       ├── pages/            # 页面（Login、Chat、Admin）
│       ├── stores/           # Pinia 状态管理
│       └── router/           # 路由配置
├── tests/                    # Python 回归测试
├── docker-compose.yml        # Docker Compose 部署
├── Dockerfile.api            # 后端 Dockerfile
├── requirements.txt          # Python 依赖
└── .env.example              # 环境变量模板
```

---

## 快速开始

### 环境要求

| 环境 | 版本 |
|---|---|
| Python | 3.11 |
| Node.js | 18+ |
| Docker Desktop | 最新版（可选，用于一键部署） |
| DashScope API Key | 必填 |

### 方式一：Docker Compose 一键部署（推荐）

#### 1. 准备配置

```bash
cp .env.example .env
```

PowerShell：

```powershell
Copy-Item .env.example .env
```

至少需要修改：

- `DASHSCOPE_API_KEY`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_BOOTSTRAP_USER_PASSWORD`

#### 2. 启动 Compose

```bash
docker compose up -d --build
```

默认访问地址：

```text
http://localhost:8080
```

默认登录账号来自 `.env` 中的 `AUTH_BOOTSTRAP_*` 配置：

- 管理员：`AUTH_BOOTSTRAP_ADMIN_USERNAME`
- 普通用户：`AUTH_BOOTSTRAP_USER_USERNAME`

#### 3. 持久化目录

Compose 会保留以下数据：

- `data/`：SQLite、会话 JSON、私有知识上传文件、客服结构化数据、md5 去重记录
- `chroma_db/`：向量库
- `logs/`：运行日志
- `redis_data`：Redis 持久化卷

### 方式二：本地开发启动

#### 1. 后端安装

```bash
conda create -n wisdomsystem-py311 python=3.11
conda activate wisdomsystem-py311
pip install -r requirements.txt
```

#### 2. 前端安装

```bash
cd web
npm install
```

#### 3. 配置环境变量

```bash
cp .env.example .env
```

至少需要修改：

- `DASHSCOPE_API_KEY`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_BOOTSTRAP_USER_PASSWORD`

**获取 API Key**：

1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 创建 API Key

#### 4. 启动 Redis（可选）

Redis 用于缓存和会话管理，不配置则自动降级到内存缓存。

```bash
D:\Redis\redis-server.exe
```

#### 5. 启动 FastAPI

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 6. 启动 Vue3 前端

```bash
cd web
npm run dev
```

开发地址：

- FastAPI Docs: `http://localhost:8000/docs`
- Vue3: `http://localhost:5173`

---

## 主要页面

| 路径 | 说明 |
|---|---|
| `/login` | 登录 / 注册 |
| `/chat` | 聊天工作台、私有知识上传、来源展示 |
| `/admin/knowledge` | 管理员知识库管理 |
| `/admin/users` | 管理员用户管理 |
| `/403` | 权限不足页 |

---

## 主要接口

### 浏览器鉴权

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 用户名/密码登录并签发 Cookie |
| POST | `/api/v1/auth/register` | 公开注册 `user` 并直接签发 Cookie |
| POST | `/api/v1/auth/logout` | 清理登录态 |
| GET | `/api/v1/auth/me` | 恢复当前登录用户 |

### 用户自作用域接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/me/sessions` | 为当前登录用户创建会话 |
| GET | `/api/v1/me/sessions` | 查询当前登录用户历史会话 |
| GET | `/api/v1/me/sessions/{session_id}` | 查询当前登录用户会话详情 |
| POST | `/api/v1/me/chat/stream` | SSE 流式聊天 |
| GET | `/api/v1/me/knowledge/chunks` | 查询当前登录用户私有 chunk |
| POST | `/api/v1/me/knowledge/documents/upload` | 上传私有知识文档并立即入库 |
| DELETE | `/api/v1/me/knowledge/chunks/{doc_id}` | 删除当前登录用户私有 chunk |

### 管理员接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/users` | 查看用户列表 |
| POST | `/api/v1/admin/users` | 创建 `user` 或 `admin` |
| GET | `/api/v1/admin/knowledge/chunks` | 分页查看 chunk，可按 `user_id` 过滤 |
| GET | `/api/v1/admin/knowledge/search` | 检索预览，可按 `user_id` 过滤 |
| POST | `/api/v1/admin/knowledge/documents/upload` | 上传共享知识文档并立即入库 |
| DELETE | `/api/v1/admin/knowledge/chunks/{doc_id}` | 删除指定 chunk |
| POST | `/api/v1/admin/knowledge/rebuild` | 清空并重建索引 |

### SSE 事件

- `answer_delta`
- `tool_event`
- `done`
- `error`

`done` 事件当前会返回 `session_id + sources`，前端据此展示引用来源。

---

## 配置说明

### 环境变量

环境变量模板统一放在根目录 `.env.example`：

- 浏览器前端不再携带静态 `FASTAPI_API_KEY`
- Vue3 前端通过 `HttpOnly` Cookie 使用 `/api/v1/auth/*`、`/api/v1/me/*`、`/api/v1/admin/*`
- `FASTAPI_API_KEY` 仅作为兼容旧接口的 deprecated 配置保留
- DashScope 调用会对 `dashscope.aliyuncs.com` 与 `.aliyuncs.com` 自动补 `NO_PROXY`
- `.env.example` 不包含本机代理配置，避免把宿主机网络策略写入模板

### chroma.yml

```yaml
collection_name: agent
persist_directory: chroma_db
k: 10
data_path: data
md5_hex_store: data/md5.txt
allow_knowledge_file_type: ["txt", "pdf", "docx", "xlsx", "csv", "md", "json"]
chunk_size: 200
chunk_overlap: 20
separators: ["\n\n", "。", ".", "?", "？", "!", " ", ""]
```

### rag.yml

```yaml
chat_model_name: qwen-max
embedding_model_name: text-embedding-v2
```

---

## 验证命令

### 后端

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services tests
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
python -m unittest tests.test_api_auth -v
python -m unittest tests.test_customer_tools -v
python -m pip check
```

### 前端

```bash
cd web
npm run build
npm run test
npx playwright test
```

### RAG 评估

```bash
conda activate wisdomsystem-py311
python tests/rag_evaluation.py
```

### 量化评测

```bash
python eval/migrate_test_cases.py
python eval/export_chunks.py --limit 1000
python eval/evaluate_retrieval.py --modes vector_only hybrid_rerank
python eval/evaluate_answer.py
python eval/evaluate_agent.py
python eval/benchmark_stream.py --mode service
python eval/generate_markdown_report.py
```

---

## 故障排除

常见问题：

- **API Key 错误**：检查 `.env` 中 `DASHSCOPE_API_KEY` 是否正确配置
- **数据库连接失败**：确认 SQLite 文件可写，Redis 服务已启动（可选）
- **ChromaDB 异常**：检查 `config/chroma.yml` 中的路径配置
- **PDF 解析失败**：Docling 模型需要联网下载，首次使用需保持网络畅通
- **新对话 404**：已修复，确保 `SessionManager.create_session` 创建会话文件
- **SSE 流式响应异常**：确认 `Content-Type` 为 `text/event-stream`
- **前端无法访问**：确认 Vite 开发服务器已启动（`npm run dev`）
- **Docker 启动异常**：检查 `wsl --version`、硬件虚拟化和 WSL 更新状态

---

## 当前版本

- 当前仓库主线版本：`v1.10`
- 版本重点：Bug 修复（新对话 404、异步流式响应）、BM25/RAG/ChatService 增强、量化评测框架、客服业务工具、Docker Compose 主部署路径

---

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
